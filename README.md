[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/license/mit/)
![License](https://img.shields.io/badge/release-0.5.0-blue.svg)
[![Play Framework](https://img.shields.io/badge/play%20framework-2.8.19-green.svg)](https://www.playframework.com/)
[![Scala](https://img.shields.io/badge/scala-2.13-green.svg)](https://www.scala-lang.org/)
[![Bootstrap](https://img.shields.io/badge/bootstrap-5.3.2-green.svg)](https://getbootstrap.com/)

## Rfiding
Rfiding is a project to restrict access to machines and doors in our hackerspace.

This project is the server part to communicate with rfiding clients.

One implementation for a client can be found at [rfiding](https://github.com/DingFabrik/rfiding).

This project is written in Scala and relies on the [Play Framework](https://www.playframework.com/). 

## Installation
 * Download a release from the [releases page](https://github.com/DingFabrik/rfiding-server/releases/).
 * Extract it.
 * Run it with some variables set:
```bash
<PATH_TO_APP>/bin/rfiding-server \
	-Dplay.http.secret.key=<changeme> \
	-Dplay.evolutions.db.default.autoApply=true \
	-Dplay.filters.hosts.allowed.0="192.168.123.42" \
	-Dplay.filters.hosts.allowed.1="mydomain.example.com"
```

### Allowed hosts

Remember to set the allowed hosts for the allowed hosts filter.
See [Play: AllowedHostsFilter](https://www.playframework.com/documentation/2.6.x/AllowedHostsFilter).
This variable represents all IPs and DNS names the app is available at.

## Update
 * Download a release from the [releases page](https://github.com/DingFabrik/rfiding-server/releases/).
 * Read the release notes.
 * Create a backup copy of `conf/application.conf` and `conf/logback.xml` in the root project.
 * Replace the content from the previous installation with the content from the release archive.
 * Move the backup copy of `conf/application.conf` and `conf/logback.xml` into the updated folder.
 * The database gets updated with the next access to the app. Data should be preserved.
