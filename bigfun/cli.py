import os
import multiprocessing
import functools

import yaml
import click
from click_help_colors import HelpColorsGroup, HelpColorsCommand
from watchdog.observers import Observer



BIGFUNCTIONS_FOLDER = 'bigfunctions'
TABLES_FOLDER = 'data'
CONFIG_FILENAME = 'config.yaml'
CONFIG = {}
if os.path.exists(CONFIG_FILENAME):
    CONFIG = yaml.safe_load(open(CONFIG_FILENAME, encoding='utf-8').read()) or {}


def get_config_value(name):
    if name in CONFIG:
        return CONFIG[name]

    text, default = {
        'default_gcp_project': ("Default GCP project where to deploy bigfunctions", "bigfunctions"),
        # 'default_datasets':    ("Default dataset(s) where to deploy bigfunctions (comma separated if many)", "eu,us,asia_east1,asia_east2,asia_northeast1,asia_northeast2,asia_northeast3,asia_south1,asia_southeast1,australia_southeast1,europe_north1,europe_west1,europe_west2,europe_west3,europe_west4,europe_west6,northamerica_northeast1,southamerica_east1,us_central1,us_east1,us_east4,us_west1,us_west2"),
        'default_datasets':    ("Default dataset(s) where to deploy bigfunctions (comma separated if many)", "eu"),
        'default_bucket':    ("Default bucket where to upload npm packages used by js functions", ""),
        'quota_management_backend': ("Backend used for quota management (none or datastore)(if you choose datastore, additionnal intallation steps are required)(if you choose none: only `max_rows_per_query` quota will be checked)", 'none'),
        'quota_contact': ("Contact which appears when user receives a Quota Error", 'paul.marcombes@unytics.io'),
        'quota_max_cloud_run_requests_per_user_per_day': ("Maximum number of 'cloud run requests' a user can make a day while calling remote functions", 1000),
    }[name]
    CONFIG[name] = click.prompt(text, default=default)
    if name == 'default_datasets':
        CONFIG[name] = CONFIG[name].split(',')
    with open(CONFIG_FILENAME, 'w', encoding='utf-8') as outfile:
        yaml.dump(CONFIG, outfile, default_flow_style=False)
    return CONFIG[name]


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='cyan'
)
def cli():
    pass


@cli.command()
@click.argument('bigfunction')
def deploy(bigfunction):
    '''
    Deploy BIGFUNCTION

    - If BIGFUNCTION = '{project}.{dataset}.{name}' then bigfunction of name {name} in bigfunctions folder will be deployed in dataset {dataset} of project {project}

    - If BIGFUNCTION = '{dataset}.{name}' then bigfunction of name {name} in bigfunctions folder will be deployed in dataset {dataset} of default project defined in `config.yaml` file. If no default dataset is defined yet, it will be prompted and saved in `config.yaml`.

    - If BIGFUNCTION = '{name}' then bigfunction of name {name} in bigfunctions folder will be deployed in default datasets of default project defined in `config.yaml` file. If these default values are not defined yet, they will be prompted and saved in `config.yaml`.

    - If BIGFUNCTION = 'ALL' then all bigfunctions contained in bigfunctions folder will be deployed in default datasets of default project in `config.yaml` file. If these default values are not defined yet, they will be prompted and saved in `config.yaml`.
    '''
    from .deploy import deploy as deploy_bigfunction
    name = bigfunction
    if name == 'ALL':
        project = get_config_value('default_gcp_project')
        datasets = get_config_value('default_datasets')
        names = [f.replace('.yaml', '') for f in os.listdir(BIGFUNCTIONS_FOLDER)]
    elif len(name.split('.')) == 1:
        project = get_config_value('default_gcp_project')
        datasets = get_config_value('default_datasets')
        names = [name]
    elif len(name.split('.')) == 2:
        project = get_config_value('default_gcp_project')
        datasets = [name.split('.')[0]]
        names = [name.split('.')[1]]
    elif len(name.split('.')) == 3:
        project = name.split('.')[0]
        datasets = [name.split('.')[1]]
        names = [name.split('.')[2]]
    else:
        raise

    bucket = get_config_value('default_bucket')

    quotas = {
        'backend': get_config_value('quota_management_backend'),
        'contact': get_config_value('quota_contact'),
    }
    if quotas['backend'] == 'datastore':
        quotas = {**quotas, **{
            'max_cloud_run_requests_per_user_per_day': get_config_value('quota_max_cloud_run_requests_per_user_per_day'),
            'whitelisted_users': [
                user.strip()
                for user in CONFIG.get('quota_whitelisted_users', '').split(',')
                if user.strip()
            ]
        }}

    for name in names:
        assert name in names, f'Could not find "{name}" in "{BIGFUNCTIONS_FOLDER}" folder'
        dataset = datasets[0]
        deploy_bigfunction(f'{project}.{dataset}.{name}', quotas, bucket)
        if len(datasets) > 1:
            deploy = functools.partial(deploy_bigfunction, quotas=quotas, bucket=bucket)
            with multiprocessing.Pool(processes=8) as pool:
                pool.map(deploy, [f'{project}.{dataset}.{name}' for dataset in datasets[1:]])


@cli.command()
@click.argument('bigfunction')
def test(bigfunction):
    '''
    Test BIGFUNCTION
    '''
    # [TODO] make some tests


@cli.command()
@click.argument('table')
def load_table(table):
    '''
    Create or replace bigquery table with data contained in data/{name}.csv

    - If TABLE = '{project}.{dataset}.{name}' then table of name {name} in 'data' folder will be deployed in dataset {dataset} of project {project}

    - If TABLE = '{dataset}.{name}' then table of name {name} in 'data' folder will be deployed in dataset {dataset} of default project defined in `config.yaml` file. If no default dataset is defined yet, it will be prompted and saved in `config.yaml`.

    - If TABLE = '{name}' then table of name {name} in 'data' folder will be deployed in default datasets of default project defined in `config.yaml` file. If these default values are not defined yet, they will be prompted and saved in `config.yaml`.

    - If TABLE = 'ALL' then all tables contained in 'data' folder will be deployed in default datasets of default project in `config.yaml` file. If these default values are not defined yet, they will be prompted and saved in `config.yaml`.
    '''
    from .load_table import load_table as upload_table
    name = table
    if name == 'ALL':
        project = get_config_value('default_gcp_project')
        datasets = get_config_value('default_datasets')
        names = [f.replace('.yaml', '') for f in os.listdir(TABLES_FOLDER) if f.endswith('.yaml')]
    elif len(name.split('.')) == 1:
        project = get_config_value('default_gcp_project')
        datasets = get_config_value('default_datasets')
        names = [name]
    elif len(name.split('.')) == 2:
        project = get_config_value('default_gcp_project')
        datasets = [name.split('.')[0]]
        names = [name.split('.')[1]]
    elif len(name.split('.')) == 3:
        project = name.split('.')[0]
        datasets = [name.split('.')[1]]
        names = [name.split('.')[2]]
    else:
        raise

    for dataset in datasets:
        for name in names:
            assert name in names, f'Could not find "{name}" in "{TABLES_FOLDER}" folder'
            upload_table(f'{project}.{dataset}.{name}')



@cli.group()
def docs():
    '''
    Generate, serve and publish documentation
    '''
    pass

@docs.command()
def generate():
    '''
    Generate markdown files for documentation from yaml bigfunctions files
    '''
    from .generate_doc import generate_doc
    generate_doc()


@docs.command()
def serve():
    '''
    Serve docs locally on http://localhost:8000
    '''
    from .generate_doc import generate_doc
    class EventHandler:
        def dispatch(self, event):
            generate_doc()
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, BIGFUNCTIONS_FOLDER, recursive=True)
    observer.start()
    generate_doc()
    os.system('mkdocs serve')
