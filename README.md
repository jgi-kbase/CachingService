# CachingService

Generic file-caching service for the KBase platform, allowing you to save the results of long-running jobs so you don't have repeat them unnecessarily.

For example, you might want to run a preprocessing algorithm on some fasta files to make them searchable. You don't want to have to do the same preprocessing on those files over and over again, and instead want to fetch previous results that you've already generated. If your app uses this service, then you can save the file ouput of a job given certain parameters and fetch that same output later given the same parameters.

It's important to note that this is only useful if the time it takes to generate a file is going to be longer than it takes to download the file from this service.

_Typical workflow:_

1. Obtain a KBase authentication token (you will use this for all cache operations).
2. Create a cache ID using your auth token and some unique identifiers for your cache (such as method names and parameters)
3. Upload, download, and delete a cache file with the cache ID

The KBase auth token is used to scope caches. Use a unique auth token for each consumer service that uses the cache server.

A **cache ID** is a unique ID that represents your auth token and a set of arbitrary JSON data that identifies the cache file (such as method name and method params). Generating an ID is fast and cheap; you can re-generate a cache ID every time you use the cache. You do not need to store cache IDs.

#### Expirations

Cache files expire after 30 days of inactivity. If the file is not downloaded or replaced within 30 days, it will get deleted.

After generating a cache ID, you have 7 days to upload a file using the ID, after which the ID will expire and you will have to re-generate it.

## API

### Create cache ID

* Path: `/v1/cache_id`
* Method: `POST`
* Required headers:
  * `Content-Type` must be `application/json`
  * `Authorization` must be your service token
* Body: arbitrary JSON data that identifies your cache

Sample request:

```sh
curl -X POST
     -H "Content-Type: application/json"
     -H "Authorization: <service_auth_token>"
     -d '{"method_name": "mymethod", "params": {"contig_length": 123}}'
     https://<caching_service_host>/v1/cache_id
```

Sample successful response:

```
{
  "cache_id": "xyzxyz",
  "status": "ok",
  "metadata": {
    "filename": "xyz.txt",
    "token_id": "<auth_url>:<username>",
    "expiration": "<unix_timestamp>"
  }
}
```

If the `metadata/filename` key in the response is `placeholder`, then you know that no file has yet been saved to this cache ID.

Sample failed response:

```
{
  "status": "error",
  "error": "Message describing what went wrong"
}
```

Use the cache ID for requests to upload/download/delete caches. Cache IDs can be re-generated any number of times.

Note that cache IDs expire after 7 days if unused.

### Upload a cache file

* Path: `/v1/cache/<cache_id>`
* Method: `POST`
* Required headers:
  * `Content-Type` should be `multipart/form-data`
  * `Authorization` must be your service token
* Body: multipart file upload data using the `'file'` field

We use `multipart/form-data` so you can pass a filename in the request.

Sample request:

```sh
curl -X POST
     -H "Content-Type: multipart/form-data"
     -H "Authorization: <service_auth_token>"
     -F "file=@myfile.zip"
     https://<caching_service_host>/v1/cache/<cache_id>
```

Sample successful response:

```sh
{"status": "ok"}
```

Sample failed response:

```sh
{
  "status": "error",
  "error": "Message describing what went wrong"
}
```

### Download a cache file

* Path: `/v1/cache/<cache_id>`
* Method: `GET`
* Required headers:
  * `Authorization` must be your service token

Sample request:

```sh
curl -X GET -H "Authorization: <service_auth_token>"
     https://<caching_service_host>/v1/cache/<cache_id>
```

A successful response will give you the complete file data with the content type of what you uploaded.

Failed responses will return JSON:

```sh
{
  "status": "error",
  "error": "Message describing what went wrong"
}
```

### Delete a cache file

* Path: `/v1/cache/<cache_id>`
* Method: `DELETE`
* Required headers:
  * `Authorization` must be your service token

Sample request:

```sh
curl -X DELETE
     -H "Authorization: <service_auth_token>"
     https://<caching_service_host>/v1/cache/<cache_id>
```

Sample successful response:

```sh
{"status": "ok"}
```

Sample failed response:

```sh
{
  "status": "error",
  "error": "Message describing what went wrong"
}
```

## Python example

_Generate a cache ID_

```py
# Be sure to set up my_service_token as a KBase authorization token
headers = {'Content-Type': 'application/json', 'Authorization': my_service_token}
# Arbitrary cache identification data
cache_data = {'method': 'method_name': 'params': 'xyz'}
endpoint = caching_server_url + '/cache_id'
resp_json = requests.post(endpoint, data=json.dumps(cache_data), headers=headers).json()
if resp_json.get('error'):
    # Some error message was received
    raise Exception(resp_json['error'])
# Success!
cache_id = resp_json['cache_id']
```

_Upload a file to a cache_

```py
endpoint = caching_server_url + '/cache/' + cache_id
# Open a file as byte encoded and use the `files` option in requests
with open('my-file.txt', 'rb') as fd_read:
    resp_json = requests.post(
        endpoint,
        files={'file': fd_read},
        headers={'Authorization': my_service_token}
    ).json()
if resp_json['status'] == 'error':
    # Some error message was received
    raise Exception(resp_json['error'])
```

_Download a file from a cache_

In this example, we stream the cache data to a local file

```py
endpoint = caching_server_url + '/cache/' + cache_id
resp = requests.get(endpoint, headers={'Authorization': my_service_token}, stream=True)
if resp.status_code == 200:
    # Success! Download the file in chunks to save memory
    with open(local_file_path, 'wb') as fd_write:
        for chunk in resp.iter_content():
            fd_write.write(chunk)
    return local_file_path
else resp.status_code == 404:
    print('cache does not exist')
else:
    print('some other error; check the response')
```

## Development & deployment

### Development and tests

Start the server with

```sh
docker-compose up
```

Once the servers are up and running, run the tests in another terminal:

```sh
make test
```

### Bucket setup

The app will use the bucket name set by the `MINIO_BUCKET_NAME` env var. If the bucket doesn't exist, the app will create it for you. If you monkey with the bucket (eg. rename or delete it) then you need to restart the server to recreate the bucket.

While docker-compose is running, you can open up `localhost:9000` to use the Minio web UI.

You can also call `docker-compose run mc` to access the Minio CLI for your running Minio instance.

#### Delete a whole bucket

To delete an entire non-empty bucket, run:

```sh
docker-compose run mc rm -r --force /data/kbase-cache
```

Restart the server afterwards to re-create the bucket.

### Administration CLI

Run the admin CLI with:

```
docker-compose run web python -m src.caching_service.admin
```

Delete all expired cache entries with:

```
docker-compose run web python -m src.caching_service.admin expire_all
```

#### Stress tests

There is a test class for stress-testing the server in `test/test_server_stress.py`. Run it with:

```sh
make stress-test
```

These tests will:
* Test gunicorn/gevent workers: Upload/download/fetch/delete 1000 small files in parallel.
* Test Minio parallelism: Upload a single 1gb file and then upload 10x 1gb files in parallel and compare times.

### How it works

* All caches have a unique ID which is a hash of their service token username, name, and an arbitrary set of JSON parameters.
* We use Minio's file metadata to store the original filename, token ID, expiration, and any other metadata we may need in the future.
* When a cache ID is generated, a placeholder (0 byte) file is created with metadata for the token ID and expiration
* Every cache file is saved to Minio under its cache ID.
* We authenticate access to a file by matching a token ID (token username + name) against a token ID stored in the metadata of an existing file with the same cache ID.
* To expire files, we read all the metadata in a bucket and delete the expired files.

### Project anatomy

* `/src/caching_service/` is the main package directory
* `/src/caching_service/server.py` is the main entrypoint for running the flask server
* `/src/caching_service/minio.py` contains utils for uploading, checking, and fetching files with Minio
* `/src/caching_service/generate_cache_id.py` contains utils for generating cache IDs from tokens/params
* `/src/caching_service/api` holds all the routes for each api version
* `/src/caching_service/hash.py` is a utility for blake2b hashing
* `/src/caching_service/authorization/` contains utilites for authorization using KBase's auth service

This app uses Flask blueprints to create separate routes for each API version.

_Dependencies:_

This project makes heavy use of [Minio](https://docs.minio.io/) using the Python Minio client.

* `requirements.txt` lists all pip requirements for running the server in all environments
* `dev-requirements.txt` lists all pip requirements for running the server in the development environment

If you install any new dependencies, be sure to re-run `docker-compose build --no-cache`.

Docker:

* `docker-compose.yaml` and `./Dockerfile` contain docker setup for all services


## References

* [Design document](docs/design.md)
