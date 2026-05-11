# Deployment Checklist

## Environment

- Set `SECRET_KEY` to a long random value.
- Set `DEBUG=false`.
- Set `ALLOWED_HOSTS` to the production domain names.
- Set `DATABASE_URL` to the managed PostgreSQL database URL.
- Set `REDIS_URL` before enabling Celery workers.
- Configure upload size limits at the platform edge and in Django.

## Database

- Provision PostgreSQL.
- Run `python manage.py migrate`.
- Confirm the `imports` migration is applied.
- Create the first admin user with `python manage.py createsuperuser`.
- Confirm automated backups are enabled.
- Confirm restore procedure is documented by the hosting provider.

## Static And Media Files

- Run `python manage.py collectstatic --noinput` when static hosting is configured.
- Configure object storage before storing uploaded source files permanently.
- Keep uploaded reconciliation source files private.
- Define a retention policy for uploaded files and generated exports.

## Security

- Require authenticated access before exposing customer data.
- Confirm tenant boundaries before onboarding multiple customers.
- Create at least one `Tenant` and `Membership` for each production user before asking them to upload data.
- Enable HTTPS-only traffic.
- Set secure cookie flags in production settings.
- Review admin access and remove unused staff accounts.

## Background Jobs

- Start Redis before enabling Celery.
- Add a Celery worker process for long-running imports.
- Add retry and timeout limits for parsing tasks.
- Monitor failed import jobs and alert on repeated failures.

## Observability

- Capture Django application logs.
- Capture request logs for upload and export routes.
- Record reconciliation run failures with import IDs.
- Set log retention according to customer data policy.

## Smoke Test

- Open the dashboard.
- Upload a POS daily CSV with a known suspended sale.
- Confirm an import file, transactions, reconciliation run, issue, and audit events are created.
- Open the run detail page.
- Download the issue CSV export.
- Confirm the CSV includes `Severity,Category,Title,Evidence,Recommended Action,Related Transactions`.
