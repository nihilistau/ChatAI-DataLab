"""Kitchen CLI for interacting with capsule snapshots."""
# @tag: kitchen,scripts,capsule

import argparse

from .capsule_snapshot import (
    list_manifests,
    list_users,
    load_capsule,
    save_capsule,
)

def main():
    parser = argparse.ArgumentParser(description="Capsule save/load CLI")
    subparsers = parser.add_subparsers(dest="command")

    save_parser = subparsers.add_parser("save", help="Save capsule state")
    save_parser.add_argument("--manifest", default="configs/capsules/onboarding.json")
    save_parser.add_argument("--snapshot", default="data/capsule-onboarding-snapshot.json")

    load_parser = subparsers.add_parser("load", help="Load capsule state")
    load_parser.add_argument("--snapshot", default="data/capsule-onboarding-snapshot.json")
    load_parser.add_argument("--manifest", default="configs/capsules/onboarding.json")

    list_parser = subparsers.add_parser("list", help="List available capsule manifests")
    list_parser.add_argument("--config_dir", default="configs/capsules")

    users_parser = subparsers.add_parser("users", help="List users for a manifest")
    users_parser.add_argument("--manifest", default="configs/capsules/onboarding.json")

    args = parser.parse_args()
    if args.command == "save":
        save_capsule(args.manifest, args.snapshot)
    elif args.command == "load":
        load_capsule(args.snapshot, args.manifest)
    elif args.command == "list":
        print(list_manifests(args.config_dir))
    elif args.command == "users":
        print(list_users(args.manifest))
    elif args.command is None:
        parser.print_help()

if __name__ == "__main__":
    main()
