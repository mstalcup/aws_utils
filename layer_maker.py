import json
import subprocess
import sys
import os
import boto3
import shutil


def install(package, include_deps=True):
    """
    run command line script to pip install a package to the /tmp directory (by default, lambda can only read/write from /tmp)
    :param package: the name of the package to pip install
    :param include_deps: setting to False will run the pip install with the '--no-deps' flag, this might be useful for
    packages with a large amount of dependencies that make it go above the lambda layer size limit
    """
    if include_deps:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, '-t', '/tmp/layers/python'])
    else:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package, '--no-deps', '-t', '/tmp/layers/python'])


def lambda_handler(event, context):
    s3_bucket = '<insert your bucket name here>'  # bucket where the layer's zip file will be stored
    package_name = 'hjson'  # name of the package you want to create a layer from (what you would pip install)
    # run pip install, write to /tmp/layers/python
    install(package_name)
    print(f'done with pip install...{os.listdir("/tmp/layers/python")}')

    shutil.make_archive(f'/tmp/{package_name}-layer', 'zip', '/tmp/layers')
    print(f'done zipping pip install location, result: {os.listdir("/tmp")}')

    s3 = boto3.client('s3')
    response = s3.upload_file(f'/tmp/{package_name}-layer.zip', s3_bucket,
                              f'{package_name}-layer.zip')
    print(f'published to s3: {response}')

    print('start publishing layer to lambda...')
    lambda_client = boto3.client('lambda')
    layer_name = f'{package_name}-layer_311'  # I like to add the runtime as a suffix so it's easy to see
    response = lambda_client.publish_layer_version(
        LayerName=layer_name,
        Content={
            'S3Bucket': s3_bucket,
            'S3Key': f'{package_name}-layer.zip'
        },
        CompatibleRuntimes=[
            'python3.11'
        ]
    )
    print(f'finished publishing lambda layer: {response}')

    return {
        'statusCode': 200,
        'body': json.dumps(f'Created layer [{layer_name}] from contents of [{s3_bucket}/{package_name}-layer.zip]')
    }
