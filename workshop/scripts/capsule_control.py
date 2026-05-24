"""Workshop CLI for interacting with relay snapshots."""
# @tag: workshop,scripts,relay

import argparse

from .capsule_snapshot import (
    list_manifests,
    list_users,
    load_relay,
    save_relay,
)

def main():
    parser = argparse.ArgumentParser(description="Relay save/load CLI")
    subparsers = parser.add_subparsers(dest="command")

    save_parser = subparsers.add_parser("save", help="Save relay state")
    save_parser.add_argument("--manifest", default="configs/relays/onboarding.json")
    save_parser.add_argument("--snapshot", default="data/relay-onboarding-snapshot.json")

    load_parser = subparsers.add_parser("load", help="Load relay state")
    load_parser.add_argument("--snapshot", default="data/relay-onboarding-snapshot.json")
    load_parser.add_argument("--manifest", default="configs/relays/onboarding.json")

    list_parser = subparsers.add_parser("list", help="List available relay manifests")
    list_parser.add_argument("--config_dir", default="configs/relays")

    users_parser = subparsers.add_parser("users", help="List users for a manifest")
    users_parser.add_argument("--manifest", default="configs/relays/onboarding.json")

    args = parser.parse_args()
    if args.command == "save":
        save_relay(args.manifest, args.snapshot)
    elif args.command == "load":
        load_relay(args.snapshot, args.manifest)
    elif args.command == "list":
        print(list_manifests(args.config_dir))
    elif args.command == "users":
        print(list_users(args.manifest))
    elif args.command is None:
        parser.print_help()

if __name__ == "__main__":
    main()
