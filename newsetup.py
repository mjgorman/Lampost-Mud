import sys
from lampost.setup.newsetup import new_setup

if __name__ != "__main__":
    print("Invalid usage")
    sys.exit(2)

setup_args = {}
for arg in sys.argv[1:]:
    try:
        name, value = arg.split(":")
        setup_args[name] = value
    except ValueError:
        print("Invalid argument format: {}".format(arg))
        sys.exit(2)

if not setup_args.get('imm_name'):
    print("Please supply an imm_name argument to identify the root user")
    sys.exit(2)

new_setup(**setup_args)
