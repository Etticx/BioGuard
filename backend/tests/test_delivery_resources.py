"""Packaging regression: backend imports must work from the Docker COPY inputs."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]

def test_container_backend_copy_includes_import_time_resources(tmp_path):
    # Recreate the backend source COPY inputs, without reading the author's model/data.
    staged=tmp_path/'backend';staged.mkdir()
    docker=(ROOT/'Dockerfile').read_text(encoding='utf-8')
    copied=[]
    for line in docker.splitlines():
        parts=line.split()
        if len(parts)==3 and parts[0]=='COPY' and parts[1].startswith('backend/') and parts[2].startswith('/app/backend'):
            for source in ROOT.glob(parts[1]):
                if source.is_file():shutil.copy2(source,staged/source.name);copied.append(source.name)
    shutil.copytree(ROOT/'web',tmp_path/'web')
    result=subprocess.run([sys.executable,'-c','from inspection_guidance import RULES; from app import app; assert len(RULES)==7'],cwd=staged,capture_output=True,text=True)
    assert result.returncode==0, f'Packaged backend cannot start with COPY inputs {copied}:\n{result.stderr}'
