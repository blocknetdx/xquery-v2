# XQuery v2.0

## Setup For Testing Milestones 1, 2 & 3

### Dependencies & Requirements

- Linux Ubuntu 20.04 LTS (or similar)
- python 3.8 or 3.9
- docker version 20.10
- docker compose version v2.3.4
- alembic 1.8.0
- running Web3 enabled node (e.g. ETH, AVAX, Sys NEVM.)
- Ensure no containers or services are listening on any of the
  following ports: `5432`, `6379`, `8080`

### Clone This Repository and Enter Cloned Repo

```shell
# --recursive flag is needed while cloning to ensure the xquery2 submodule is  
# also cloned.

git clone --recursive https://github.com/blocknetdx/xquery-v2-testing

# If this repo has previously been cloned and the original xquery2 repo
# has since been updated, the xquery2 submodule in this repo can be
# updated with:

git submodule update

# Enter the clone of the xquery-v2-testing repo:

cd xquery-v2-testing
```

### Launch Postgres, Redis & Hasura containers

```shell
cp .env.template .env

# Review the env variables set it .env; modify them if desired

./run.sh
```

### Enter xquery2 submodule
```shell
cd xquery2
```

### set up & activate virtual environment

```shell
sudo apt install python3-virtualenv
virtualenv -p python3 ./.venv
source .venv/bin/activate

pip install -r requirements.txt
```

#### Errors running pip install -r requirements.txt

If you get errors running `pip install -r requirements.txt`, see the
following:

> XQuery requires the `psycopg2` python package, which is compiled from source and thus has 
> additional system prerequisites (C compiler, system dev packages).
> See [here](https://www.psycopg.org/docs/install.html#install-from-source).

The required system packages can be install with:
```shell
sudo apt install build-essential python3-dev libpq-dev gcc
```

> Alternatively, install the precompiled `psycopg2-binary` python
> package instead, like this:

Edit `requirements.txt` and change this line:
```
psycopg2==2.9.3
```
to this:
```
psycopg2-binary==2.9.3
```
Then issue once again:
```shell
pip install -r requirements.txt
```

### Configuration

All configurable settings are consolidated in `xquery2/xquery/config.py`. Generally, no other files need to be modified!

The following options (with default value) are available and can be adjusted in the configuration file.
Alternatively, each option can also be set via its corresponding env variable. See details bellow:

```python
CONFIG = {
    # Database settings
    "DB_HOST": os.getenv("DB_HOST", "localhost"),
    "DB_PORT": os.getenv("DB_PORT", 5432),
    "DB_USERNAME": os.getenv("DB_USERNAME", "root"),
    "DB_PASSWORD": os.getenv("DB_PASSWORD", "password"),
    "DB_DATABASE": os.getenv("DB_DATABASE", "debug"),
    "DB_SCHEMA": os.getenv("DB_SCHEMA", "public"),

    # Redis cache settings
    "REDIS_HOST": os.getenv("REDIS_HOST", "localhost"),
    "REDIS_PORT": os.getenv("REDIS_PORT", 6379),
    "REDIS_PASSWORD": os.getenv("REDIS_PASSWORD", "password"),
    "REDIS_DATABASE": os.getenv("REDIS_DATABASE", 0),

    # Controller
    "XQ_NUM_WORKERS": os.getenv("XQ_NUM_WORKERS", 8),
    
    # web3 provider RPC url
    "API_URL": os.getenv("API_URL", "http://localhost:8545/"),
    # "API_URL": os.getenv("API_URL", "https://cloudflare-eth.com/v1/mainnet"),  # ETH
    # "API_URL": os.getenv("API_URL", "https://api.avax.network/ext/bc/C/rpc"),  # AVAX
    # "API_URL": os.getenv("API_URL", "https://rpc.syscoin.org/"),  # SYS
}
```

The `xquery2/xquery/config.py` file included in this repo should be considered
as an example/template. Feel free to change configs as desired.
For example, the web3 provider RPC URLs in this template config are as
follows:
```py
    # web3 provider RPC url
    "API_URL": os.getenv("API_URL", "http://localhost:8545/"),
    # "API_URL": os.getenv("API_URL", "https://cloudflare-eth.com/v1/mainnet"),  # ETH
    # "API_URL": os.getenv("API_URL", "https://api.avax.network/ext/bc/C/rpc"),  # AVAX
    # "API_URL": os.getenv("API_URL", "https://rpc.syscoin.org/"),  # SYS
```
Setting `API_URL` as above configures XQuery to fetch blockchain data from
http://localhost:8545/ . This will work well if you plan to test XQ's
indexing of Sys NEVM chain and Sys NEVM is
running locally and the blockchain data of NEVM is available via RPC
calls to port 8545 of *localhost*. If Sys NEVM is running locally in a
docker container, and port 8545 is only accessible on the container itself (not on
*localhost*), then you'll need to replace *localhost* with the IP of
the SYS container. If NEVM is not running locally,
you might want to set the `API_URL` to https://rpc.syscoin.org/,
though that source of NEVM data will be rate limited.
If you want to test indexing of AVAX while gathering AVAX blockchain data from the public
AVAX blockchain source, "https://api.avax.network/ext/bc/C/rpc", you
can set your `API_URL` to that. That works fine, but that public
source of AVAX data is rate limited. If you have
AVAX running locally and you want to ensure AVAX indexing speed is not
limited by the public source of AVAX blockchain data, you may wish to set the
`API_URL` to something like `http://172.31.11.28:9650/ext/bc/C/rpc`
...where `172.31.11.28` is the IP of the local `avax` container.<br>
NOTE: the values of the environment variables like `API_URL` set in `xquery2/xquery/config.py`
can be overridden by passing the env variable on the command line. See [Run Multiple Instances Simultaneously](https://github.com/blocknetdx/xquery-v2-testing/blob/main/README.md#run-multiple-instances-simultaneously-example) for examples.

## Database

## Basic Example - index *only one* blockchain
(Skip to [Run Multiple Instances Simultaneously](https://github.com/blocknetdx/xquery-v2-testing/blob/main/README.md#run-multiple-instances-simultaneously-example) if you plan to run indexing on multiple chains simultaneously).

Run the following commands to create the database tables:

```shell
alembic -n default -c alembic/alembic.ini revision --autogenerate -m 'creating schema'

alembic -n default -c alembic/alembic.ini upgrade head
```
NOTE, If the first `alembic` command above returns an error like this:<br>
`ERROR [alembic.util.messaging] Target database is not up to date.`<br>
it means you have already run that `alembic` command in this environment, so 
you can skip running that alembic command and go directly to the second 
`alembic` command. 

### Verify Setup

Optionally, test the environment and configuration:

```shell
python -m test_setup
```
If the above command returns something like the following, the setup
is correct:
```
06:09:17.0905 INFO  [MainThread 2178926] xquery.util.misc: Processing
time of 'main()': 0.3918 seconds.
```
If it returns errors, there are errors in the setup.

## Run Example

Run one of the preconfigured examples, Pangolin (PNG) Exchange on Avalanche or Pegasys (PSYS) Exchange on Syscoin:

```shell
python -m run_png 2> run_png.log &
python -m run_psys 2> run_psys.log &
```

The above commands start the indexing of AVAX/Sys NEVM blockchain into a
database stored on a (temporary) volume attached to the `xquery-pg`
(postgres) container.
Logs generated by `python -m run_png` or `python -m run_psys` are streamed to STDERR, which is why
this example redirects STDERR to a `.log` file with `2> run_png.log`
or `2> run_psys.log`. To free the Linux terminal, these examples run the
`run_png` or `run_psys` module in the background with `&` at the end.

To watch the streaming logs, you can issue:
```shell
# For indexing avax/pangolin:
tail -f run_png.log

# For indexing Sys NEVM/Pegasys:
tail -f run_psys.log 
```
Then issue ^C to interrupt the scrolling logs.
To interrupt the `python -m run_png` or `python -m run_psys` command:
```shell
# bring the run_png or run_psys process to the foreground:

fg

# then interrupt the process by issuing ^C
```

(Instead of issuing `python -m run_png 2> run_png.log &` or `python -m run_psys 2> run_psys.log &`, one could alternatively open a `tmux` window, activate the same
virtual environment there with `source .venv/bin/activate`, then issue
`python -m run_png` or `python -m run_psys` in the tmux window and let the logs scroll within the tmux window.)

## Run Multiple Instances Simultaneously example

In a terminal window (or tmux window) dedicated to indexing avax/pangolin, run the following commands in the `xquery2` dir to create a separate database schema for Pangolin.
Note, when you launch a new terminal window, `.venv` won't be activated, so you'll need to issue this command in the `xquery2` directory:
```shell
./.venv/bin/activate
```
Create a database schema for Pangolin:
```shell
DB_SCHEMA="xgraph_png" alembic -n default -c alembic/alembic.ini revision --autogenerate -m 'creating schema for Pangolin'
alembic -n default -c alembic/alembic.ini upgrade head
```
In the same avax/pangolin window, launch the indexer:
```shell
DB_SCHEMA="xgraph_png" API_URL="http://<avax-container-IP>:9650/ext/bc/C/rpc" REDIS_DATABASE=0 python -m run_png 2> run_png.log &
```
If avax is running locally, replace `<avax-container-IP>` with the IP of the local avax container, which can be found like this:
```shell
docker inspect exrproxy-env-avax-1 | grep IPv4
```

Then, in a new terminal window dedicated to Syscoin NEVM/Pegasys indexing, run the following commands in the `xquery2` dir to create a separate database schema for Pegasys.
Note, when you launch a new terminal window, `.venv` won't be activated, so you'll need to issue this command in the `xquery2` directory:
```shell
./.venv/bin/activate
```
Create a database schema for Pegasys:
```shell
DB_SCHEMA="xgraph_psys" alembic -n default -c alembic/alembic.ini revision --autogenerate -m 'creating schema for Pegasys'
alembic -n default -c alembic/alembic.ini upgrade head
```
In the same Syscoin NEVM/Pegasys window, launch the indexer:

```shell
DB_SCHEMA="xgraph_psys" API_URL="http://<SYS-container-IP>:8545/" REDIS_DATABASE=1 python -m run_psys 2> run_psys.log &
```
If SYS is running locally, replace `<SYS-container-IP>` with the IP of the local SYS container, which can be found like this:
```shell
docker inspect exrproxy-env-SYS-1 | grep IPv4
```

### Verify Indexed Data in Hasura Console

#### Optional hasura basic config (recommended)

Optionally, a very basic configuration can be applied to Hasura by using the following script
This needs to be run from the project root directory (`xquery2`) with *venv* activated:

```shell
python -m contrib.init_hasura
```

Find the IP of the server where XQuery v2 is running:
```
curl ifconfig.co
# OR
curl ifconfig.io
```
Note the IP of your server, which we'll refer to here as `<SERVER-IP>`

Navigate in a web browser to:
```
http://<SERVER-IP>:8080/console
```
This should give you a graphical Hasura GraphQL interface to the
database indexed by XQuery v2. You can make specific queries for
specific blocks through this GUI, then compare the query results to
the information given in Blockchain Explorers.

#### Track Tables in Hasura Console

If you did not apply the Optional hasura basic config above, the following applies:

The first time you navigate in a web browser to
`http://<SERVER-IP>:8080/console`, you'll probably see the message,
"Looks like you do not have any tables" under the **API** tab of the
console, and a suggestion to "Click the **Data** tab on top to create tables." Follow this
suggestion and click the **Data** tab. The initial Hasura Console message will
look something like this:

![Hasura Console 1](https://github.com/blocknetdx/xquery-v2-testing/blob/main/img/hasura-1.png?raw=true) 

After clicking the **Data** tab, click the **public** tab on the left.
You should now see a page something like
this:

![Hasura Console 2](https://github.com/blocknetdx/xquery-v2-testing/blob/main/img/hasura-2.png?raw=true) 

On this screen you should see an option to track a number of available
tables. Click, "Track All"

In the previous version of `xquery2`, the main table of interest was the `xquery` table, which is where
one could query for a variety of indexed EVM data. It seems the
`xquery` table is not utilized or populated in the latest version of
`xquery2` (confirmed w/ Riku), but lots of interesting data is
available for querying in the other tables and aggregates.

## Tests

> WARNING: Some tests currently affect the state of the cache and database. Only run on a development setup!

> Some tests only run on Avalanche (AVAX) currently

```shell
pytest --collect-only tests/

pytest -v tests/
pytest -v -rP tests/

pytest -v -k="cache" tests/
pytest -v -k="filter" tests/
pytest -v -k="indexer" tests/
pytest -v -k="middleware" tests/
```

## Benchmarks

```shell
python -m bench.bench_cache_redis
python -m bench.bench_fetch_token
python -m bench.bench_fetch_token_batched
python -m bench.bench_get_block
python -m bench.bench_get_block_batched
python -m bench.bench_get_logs
python -m bench.bench_serialize
```

## Deactivate Virtual Environment When Finished

```shell
deactivate
```
