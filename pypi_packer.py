import argparse
import os
import shutil

from subprocess import Popen, PIPE

# Instantiate the parser
parser = argparse.ArgumentParser(description='packer arg parser')
parser.add_argument("--server",
                    help="pypi server address",
                    default="127.0.0.1")
parser.add_argument("--path",
                    help="pypi server package dir full path ",
                    default="/var/lib/pypi/packages")
parser.add_argument("-u", "--user",
                    help="pypi server host username")
parser.add_argument("-p", "--pass",
                    help="pypi server host password")

args = parser.parse_args()

# Delete dist dir if it exists
dist_path = os.path.join(os.getcwd(), 'dist')
if os.path.exists(dist_path):
    shutil.rmtree(dist_path)

# Creating dist package using setup.py
sdist = ['python', 'setup.py', 'sdist']
try:
    p = Popen(sdist, stdout=PIPE)
    output, error = p.communicate()
except Exception as e:
    raise e
else:
    if not error:
        print("pip installable successfully created under dist directory")
    else:
        raise error

# Upload dist package to pypi server's package container directory
if args.server in ['localhost', '127.0.0.1']:
    for _file in os.listdir(dist_path):
        src_file = os.path.join(dist_path, _file)
        shutil.copy(src_file, args.path)
