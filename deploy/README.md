# Keeping the Render database

Render's free plan has no permanent disk: every deploy or restart starts with an empty
`/tmp`, so accounts and practice history would be lost. The container therefore runs
[Litestream](https://litestream.io), which copies every change of the SQLite database to
free S3-compatible storage and restores it when the app starts.

- `deploy/start.sh` restores the database (if a copy exists), then runs the app under
  `litestream replicate`, which uploads changes about once a second and once more when
  Render stops the app.
- `deploy/litestream.yml` names the database and the bucket, both from environment variables.
- Without `LITESTREAM_BUCKET` the app still starts, but warns that nothing is backed up.

## One-time setup (Backblaze B2, 10 GB free)

1. Create a Backblaze account and a **private** B2 bucket, for example `tempo-db`.
   In the bucket's lifecycle settings choose **Keep only the last version of the file**.
2. Note the bucket's **Endpoint**, for example `s3.eu-central-003.backblazeb2.com`.
   The region is the middle part, for example `eu-central-003`.
3. Under **Application Keys**, add a key that can **Read and Write** only this bucket.
   Keep the `keyID` and `applicationKey` private.
4. In Render, open the service, then **Environment**, and add:

   | Key | Value |
   |---|---|
   | `LITESTREAM_BUCKET` | the bucket name |
   | `LITESTREAM_ENDPOINT` | the bucket's endpoint |
   | `LITESTREAM_REGION` | the region from the endpoint |
   | `LITESTREAM_ACCESS_KEY_ID` | the key's `keyID` |
   | `LITESTREAM_SECRET_ACCESS_KEY` | the key's `applicationKey` |

   Keep `TEMPO_DATABASE` (for example `/tmp/tempo.sqlite`).
5. Save and deploy. The deploy log shows Litestream starting; the bucket gains a `tempo/` folder.

Cloudflare R2 works the same way: endpoint `<account-id>.r2.cloudflarestorage.com`, region `auto`.

## Notes

- Run one instance only. Two instances writing to the same bucket would overwrite each other.
- Changes from the last second before a crash can be lost; a normal deploy or restart loses nothing.
- If the storage keys are wrong, the start fails instead of running with an empty database:
  check the Render log, fix the variables and deploy again.
