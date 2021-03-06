#!/usr/bin/env python
"""Update conda packages on binstars with latest versions for multiple platforms.

"""
import os
import re
import subprocess

import toolz as tz
import yaml


CONFIG = {
  "binstar_user": "bcbio",
  "binstar_repo": "https://conda.binstar.org/bcbio",
  "targets": ["linux-64", "osx-64"]}

def main():
    config = CONFIG
    subprocess.check_call(["conda", "config", "--add", "channels", config["binstar_repo"]])
    for name in sorted([x for x in os.listdir(os.getcwd()) if os.path.isdir(x)]):
        meta_file = os.path.join(name, "meta.yaml")
        if os.path.exists(meta_file):
            version, build = _meta_to_version(meta_file)
            needs_build = _needs_upload(name, version, build, config)
            if needs_build:
                _build_and_upload(name, needs_build, config)

def _build_and_upload(name, platforms, config):
    """Build package for the latest versions and upload to binstars on all platforms.
    """
    print name, platforms
    fname = subprocess.check_output(["conda", "build", "--output", name]).strip()
    cur_platform = os.path.split(os.path.dirname(fname))[-1]
    if not os.path.exists(fname):
        subprocess.check_call(["conda", "build", "--no-binstar-upload", name])
    for platform in platforms:
        out = ""
        if platform == cur_platform:
            plat_fname = fname
        else:
            plat_fname = fname.replace("/%s/" % cur_platform, "/%s/" % platform)
            out_dir = os.path.dirname(plat_fname)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            if not os.path.exists(plat_fname):
                out = subprocess.check_output(["conda", "convert", fname, "-o", out_dir, "-p", platform])
        if os.path.exists(plat_fname):
            subprocess.check_call(["binstar", "upload", "-u", config["binstar_user"], plat_fname])
        else:
            if not out.find("WARNING") and not out.find("has C extensions, skipping"):
                raise IOError("Failed to create file for %s on %s" % (name, platform))
            else:
                print "Unable to prepare %s for %s because it contains C extensions" % (name, platform)

def _needs_upload(name, version, build, config):
    """Check if we need to upload libraries for the current package and version.
    """
    pat = re.compile("%s-(?P<version>[\d\.a-zA-Z]+)-.*_(?P<build>\d+).tar.*" % name)
    try:
        info = subprocess.check_output(["binstar", "show", "%s/%s/%s" % (config["binstar_user"], name, version)])
    # no version found
    except subprocess.CalledProcessError:
        info = ""
    cur_packages = []
    for line in (x for x in info.split("\n") if x.strip().startswith("+")):
        plat, fname = os.path.split(line.strip().split()[-1])
        m = pat.search(fname)
        cur_version = m.group("version")
        cur_build = m.group("build")
        if version == cur_version and int(cur_build) == int(build):
            cur_packages.append(plat)
    return sorted(list(set(config["targets"]) - set(cur_packages)))

def _meta_to_version(in_file):
    """Extract version information from meta description file.
    """
    with open(in_file) as in_handle:
        config = yaml.safe_load(in_handle)
    return (tz.get_in(["package", "version"], config),
            tz.get_in(["build", "number"], config, 0))

if __name__ == "__main__":
    main()
