# Database integration

The current gakuseiBOT runtime does not use this directory for database access.
There is no active Bun/Node.js database client in the supported runtime.

If database support is added in the future:
- keep credentials in environment variables or deployment secrets;
- never commit passwords or connection strings;
- add an explicit dependency manifest and tests;
- document the schema and migration process before enabling it in production.
