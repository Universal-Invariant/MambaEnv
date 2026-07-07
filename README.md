## Helps manage Mamba environments

1. Can backup some or all environments easily with timestamp and no redundant backups are saved.
2. Can easily compare packages in between environments including seeing latest version.
3. Creates a bash or batch file which can help remove mamba+pip installs in the same env easily. Note that this isn't necessarily safe and requires ensuring no unwanted package is removed.



```
usage: main.py [-h] [--all] [--fix] [--backup] [-c] [envs ...]

Audit, Backup, and Fix environments.

positional arguments:
  envs         List of environments to check

options:
  -h, --help   show this help message and exit
  --all        Parse all environments found in mamba
  --fix        Output batch commands to fix environments
  --backup     Include commands to create YML backups
  -c, --clean  Only show packages that need action
```


```
:: Fetching data for environment: bark...
:: Fetching data for environment: chess...

Legend:
  RP M/P  -> Redundant Pip (Installed in both Mamba & Pip. Clean up Pip!)
  MM ?/P  -> Move to Mamba  (Pip-only, but package exists in Mamba channels)
  ! P_VER -> Pure Pip Unique (Pip-only, missing from Mamba channels entirely)
  -       -> Not installed in this environment

Package                        | Latest     | bark                           | chess
--------------------------------------------------------------------------------------------------------------
absl-py                        |            | -                              | ! 2.2.1
accelerate                     |            | -                              | ! 1.5.2
aiocache                       |            | -                              | ! 0.12.3
aiofiles                       |            | -                              | ! 24.1.0
aiohappyeyeballs               |            | -                              | ! 2.6.1
aiohttp                        |            | -                              | ! 3.11.14
aiohttp_socks                  |            | -                              | ! 0.11.0
aiosignal                      |            | -                              | ! 1.3.2
alembic                        |            | -                              | ! 1.15.2
altgraph                       |            | -                              | ! 0.17.4
annotated-types                |            | -                              | ! 0.7.0
anthropic                      |            | -                              | ! 0.71.0
antlr4-python3-runtime         |            | -                              | ! 4.9.3
anyascii                       |            | -                              | ! 0.3.2
anyio                          |            | 4.12.1                         | ! 4.9.0
appdirs                        |            | -                              | ! 1.4.4
apscheduler                    |            | -                              | ! 3.11.0
argon2-cffi                    |            | -                              | ! 23.1.0
argon2-cffi-bindings           |            | -                              | ! 21.2.0
argostranslate                 |            | -                              | ! 1.11.1
argostranslategui              |            | -                              | ! 1.6.5
arrow                          |            | -                              | ! 1.3.0
asgiref                        |            | -                              | ! 3.8.1
astor                          |            | -                              | ! 0.8.1
asttokens                      |            | 3.0.1                          | ! 3.0.0
astunparse                     |            | -                              | ! 1.6.3
async-lru                      |            | -                              | ! 2.0.5
async-timeout                  |            | -                              | ! 5.0.1
attrs                          |            | -                              | ! 25.3.0
audioread                      |            | -                              | ! 3.0.1
authlib                        |            | -                              | ! 1.5.1
auto-py-to-exe                 |            | -                              | ! 2.48.1
autopep8                       |            | -                              | ! 2.3.2
av                             |            | -                              | ! 14.2.0
babel                          |            | -                              | ! 2.17.0
backcall                       |            | -                              | ! 0.2.0
backoff                        |            | -                              | ! 2.2.1
backports                      |            | 1.0                            | -
backports.tarfile              |            | 1.2.0                          | -
backports.zstd                 |            | 1.3.0                          | -
bark                           | 0.1.5      | ! 0.0.1a0                      | -
bcrypt                         |            | -                              | ! 4.3.0
beautifulsoup4                 |            | -                              | ! 4.13.3
bidict                         |            | -                              | ! 0.23.1
bitarray                       |            | -                              | ! 3.2.0
black                          |            | -                              | ! 25.1.0
blake3                         |            | -                              | ! 1.0.8
bleach                         |            | -                              | ! 6.2.0
blinker                        |            | -                              | ! 1.9.0
blis                           |            | -                              | ! 1.3.3
boto3                          | 1.43.41    | ! 1.42.63                      | ! 1.37.22
botocore                       | 1.43.41    | ! 1.42.63                      | ! 1.37.22
botorch                        |            | -                              | ! 0.13.0
...
Total Listed Packages/Total Packages = 800/811
```
