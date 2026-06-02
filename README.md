# Kolibri installer source for Debian

To install and subscribe to updates for Debian/Ubuntu/Raspbian, visit our PPA:

[https://launchpad.net/~learningequality/+archive/ubuntu/kolibri](https://launchpad.net/~learningequality/+archive/ubuntu/kolibri)

## Self-hosted Debian repository

In addition to the Launchpad PPA, Kolibri is available from a self-hosted
Debian repository published to GitHub Pages. This repository is independent
of Launchpad and offers two suites:

- **stable** — promoted releases only
- **prerelease** — alpha/beta/rc builds, published within minutes of a build

### Adding the repository

Download and trust the signing key:

```
curl -fsSL https://learningequality.github.io/kolibri-installer-debian/pubkey.asc \
  | sudo tee /usr/share/keyrings/kolibri-debian-keyring.asc > /dev/null
```

### Installing from the stable suite

```
echo "deb [signed-by=/usr/share/keyrings/kolibri-debian-keyring.asc] https://learningequality.github.io/kolibri-installer-debian stable main" \
  | sudo tee /etc/apt/sources.list.d/kolibri.list
sudo apt update
sudo apt install kolibri
```

### Installing from the prerelease suite

```
echo "deb [signed-by=/usr/share/keyrings/kolibri-debian-keyring.asc] https://learningequality.github.io/kolibri-installer-debian prerelease main" \
  | sudo tee /etc/apt/sources.list.d/kolibri-prerelease.list
sudo apt update
sudo apt install kolibri
```

> **Note:** Only the most recent version is kept in each suite. To switch
> from `prerelease` to `stable`, replace the sources entry and run
> `sudo apt update && sudo apt install kolibri`.

## Development roadmap

Decisions (some pending):

* This is Python 3.
* All dependencies are bundled.
* `python3-cryptography` is a suggested dependency
* How do we get rid of bundled c-extensions upstream (in Python pkg) and replace them with real dependencies

## Installation instructions

Full installation instructions:

[http://kolibri.readthedocs.io/](http://kolibri.readthedocs.io/en/latest/install.html#debian-ubuntu)


## Building

Either kind of build needs a kolibri tar file. These can be found as an asset in Kolibri releases on Github. Find the URL for the asset and then use the following command to download it:
```
make get-tar tar=<tar-asset-url>
```

If you have previously built on your machine, be sure to run:
```
make clean
```
To clean up any previous dist files and folders.

### Building a binary

To build the binary (Debian file), first install required dependencies:
```
sudo apt install -y devscripts debhelper dh-python python3-all python3-pytest po-debconf python3-setuptools python3-pip build-essential
```

Then run:
```
make kolibri.deb
```

This will build the debian file into the `dist` folder.

### Running tests

Install the project with test dependencies:
```
pip install -e ".[test]"
```

Then run:
```
python3 -m pytest tests/ -v
```

### Building sources

This is primarily used to build sources for uploading to launchpad to release to the PPA.
Install required dependencies:
```
sudo apt install -y devscripts debhelper python3-pip dput dh-python python3-all python3-pytest
```

Ensure that you have registered your GPG key with your launchpad account and that you are authorized to release to the kolibri-proposed PPA.

To build and upload the package run this command:
```
GPG_PASSPHRASE="<passphrase for your GPG key>" make commit-new-release
```

To just build the signed sources run this command:
```
GPG_PASSPHRASE="<passphrase for your GPG key>" make kolibri.changes
```
