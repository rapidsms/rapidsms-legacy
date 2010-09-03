PLEASE NOTE
===========

1) the old rapidsms codebase (aka tusker) that has been living in http://github.com/rapidsms/rapidsms HAS BEEN MOVED to http://github.com/rapidsms/rapidsms-legacy -- if your clone or fork is still in use, you should update your repository's remote/origin


2) a COMBINED repository of the contents of http://github.com/rapidsms/rapidsms-core-dev and http://github.com/rapidsms/rapidsms-contrib-apps-dev HAS REPLACED the old codebase in http://github.com/rapidsms/rapidsms

('search' and 'training' apps that were in http://github.com/rapidsms/rapidsms-contrib-apps-dev HAVE BEEN REMOVED and are now submodules of http://github.com/rapidsms/rapidsms-community-apps-dev)

3) http://github.com/rapidsms/rapidsms-core-dev and http://github.com/rapidsms/rapidsms-contrib-apps-dev WILL REMAIN UNCHANGED until the 1.0 release but should now be considered DEPRECATED.


4) pypi package will now install from http://github.com/rapidsms/rapidsms

Overview
========

RapidSMS is a Free and Open Source framework for developing short message-based
applications.

  * RapidSMS is a messaging development framework, in the same way that
    Django or Rails are web development frameworks.

  * RapidSMS is designed to do the heavy lifting for you. You implement your
    application logic, and RapidSMS takes care of the rest.

  * RapidSMS is designed specifically to facilitate building applications
    around mobile SMS.

  * ... but it supports pluggable messaging backends, including IRC and HTTP,
    and more are possible (e.g. email).

  * RapidSMS is Open Source and is written in Python.

  * RapidSMS integrates with Django, allowing you to easily develop web-based
    views of your messaging app.

  * RapidSMS is designed to scale efficiently.

  * RapidSMS provides (or will eventually provide) core support for message
    parsing, i18n, and more.
