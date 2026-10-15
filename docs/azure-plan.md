# Azure deployment plan

Status: **plan only. Nothing is deployed live.** No Azure resources exist for this project and no Azure credentials are in the repo.

## Architecture

```
 analyst / script
       |  POST /compare (npz upload)  or  blob upload
       v
 +-----------------------------+        +------------------------------+
 | App Service (Linux, B1)     | -----> | Storage account              |
 | FastAPI app (uvicorn)       | <----- |  container: input   (npz,    |
 | system-assigned identity    |        |    GeoTIFF)                  |
 +-----------------------------+        |  container: outputs (json,   |
       |                                |    csv, png)                 |
       v                                +------------------------------+
 Application Insights (logs, failures, alert)
```

The app already runs locally and in CI with the same code. Azure only hosts it and gives it storage; the NDVI logic does not change.

## Compute and storage choices

| Choice | Reason |
|---|---|
| App Service Linux, B1 (or F1 for a demo) | One stateless FastAPI process, no containers or cluster to manage, cheap, built-in HTTPS |
| Blob Storage, two containers (`input`, `outputs`) | Files are blobs, not rows; no database needed. Separate containers allow separate lifecycle rules and access |
| Standard LRS, hot tier | Small data, single region is enough for this scope |

## Identity and secrets

- The web app uses a system-assigned managed identity, so no connection strings or keys are stored anywhere.
- The identity gets **Storage Blob Data Contributor** scoped to the storage account only.
- Nothing secret lives in the repo; `.env.example` holds only the decline threshold.
- Key Vault is added only if a real secret (third-party API key etc.) appears later.
- GitHub deploys with OIDC federated credentials, not a stored publish profile or password.

## Monitoring

- Application Insights attached to the web app (request rate, failures, latency, exceptions).
- One alert rule: failed requests (HTTP 5xx) count > 0 over 5 minutes, notify by email action group.
- Invalid-input requests return 422 by design and are not counted as failures.

## Deployment steps (manual, not yet run)

```
az group create -n rg-ndvi -l centralindia
az storage account create -n <uniquestorage> -g rg-ndvi --sku Standard_LRS
az storage container create --account-name <uniquestorage> -n input --auth-mode login
az storage container create --account-name <uniquestorage> -n outputs --auth-mode login
az appservice plan create -n plan-ndvi -g rg-ndvi --is-linux --sku B1
az webapp create -n <uniqueapp> -g rg-ndvi -p plan-ndvi --runtime "PYTHON:3.11"
az webapp config set -n <uniqueapp> -g rg-ndvi --startup-file "uvicorn app:app --host 0.0.0.0 --port 8000"
az webapp config appsettings set -n <uniqueapp> -g rg-ndvi --settings NDVI_DECLINE_THRESHOLD=0.05
az webapp identity assign -n <uniqueapp> -g rg-ndvi
az role assignment create --assignee <principalId> --role "Storage Blob Data Contributor" \
  --scope $(az storage account show -n <uniquestorage> -g rg-ndvi --query id -o tsv)
```

Deploy workflow (to be added as `.github/workflows/deploy.yml`, `workflow_dispatch` only so nothing deploys on push):

1. Create an Entra app registration and add a federated credential for `repo:Saurabh-1885/Cerevyn-Chitkara-2311981465-PS07:ref:refs/heads/main`.
2. Give that app Contributor on `rg-ndvi`.
3. Set repo **variables** (not secrets): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_WEBAPP_NAME`.
4. Workflow uses `azure/login@v2` with those variables (`permissions: id-token: write`), then `azure/webapps-deploy@v3`.

## Cost control assumptions

- B1 (about one small VM) or free F1 tier; stop the web app when not demoing.
- Blob lifecycle rule: delete blobs in `outputs` older than 30 days.
- Budget alert on the resource group at a low monthly amount (e.g. 500 INR) with email at 80% and 100%.
- Inputs are small synthetic arrays, so storage and egress cost is negligible.

## Scaling to real satellite tiles

- Store tiles as cloud-optimised GeoTIFF (COG) in Blob Storage and read only the farm polygon's window with `rasterio` windowed reads instead of loading whole scenes.
- Build the farm mask by rasterising the farm boundary to the tile grid; take cloud validity from the product's scene classification band.
- Process tiles in chunks and accumulate sums and counts, so memory stays flat for large areas.
- Move heavy runs from the request path to a queue plus a worker (Container Apps job or Functions) once a single request exceeds the App Service timeout.
- Reproject both dates to one grid first; the current code requires identical shapes and rejects anything else.
