"""Online snapshots and offline restoration. Restores invalidate all saved sessions."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3
from records import Records

def inspect_backup(path):
    path=Path(path).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValueError("Backup integrity check failed.")
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"users","reports","photos","sessions"}<=tables:raise ValueError("This is not a BioGuard backup.")
        return {table:db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("users","reports","photos")}

def restore(source,directory):
    source=Path(source).resolve(strict=True);directory=Path(directory).resolve();counts=inspect_backup(source)
    records=Records(directory);directory.mkdir(parents=True,exist_ok=True)
    if source==records.database.resolve():raise ValueError("Choose a backup file, not the active database.")
    snapshot=records.backup_database() if records.database.exists() else None
    # The caller must stop the backend. SQLite backup copies BLOB evidence and schema together.
    with closing(sqlite3.connect(source.as_uri()+"?mode=ro",uri=True)) as src,closing(sqlite3.connect(records.database)) as target:
        src.backup(target);target.execute("DELETE FROM sessions");target.commit()
    records.initialize(False)
    return {"restored":counts,"pre_restore_backup":snapshot}

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('action',choices=['create','inspect','restore']);cli.add_argument('--data-dir',type=Path,default=Path(__file__).parent/'data');cli.add_argument('--source',type=Path);cli.add_argument('--backend-stopped',action='store_true');args=cli.parse_args()
    if args.action=='create':
        store=Records(args.data_dir);store.initialize(False);print(store.backup_database())
    elif args.action=='inspect':
        if not args.source:cli.error('--source is required')
        print(inspect_backup(args.source))
    else:
        if not args.source or not args.backend_stopped:cli.error('Stop the backend, then pass --source and --backend-stopped')
        print(restore(args.source,args.data_dir))
