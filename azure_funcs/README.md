## Azure funcs

You can run the VGI_API locally via the Azure Function, although for development it is recommended to run it directly from the [vgi_api](../vgi_api/README.md) directory.

## Dependencies

1. Install [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v3%2Cmacos%2Ccsharp%2Cportal%2Cbash%2Ckeda). On mac you can use brew:

```bash
brew tap azure/functions
brew install azure-functions-core-tools@3
# if upgrading on a machine that has 2.x installed:
brew link --overwrite azure-functions-core-tools@3
```

2. Create a virtual environment while in the same directory as this README.

```bash
python -m venv .venv
```

3. Activate the environment

```bash
source .venv/bin/activate
```

4. Install requirements

```bash
pip install -r requirements.txt
```

5. Install additional requirements (This is automated when deploying to Azure)
```bash
pip install ../vgi_api
```

### Run the function

First we need to configure environment variables

```bash
export NETWORKS_DATA_CONTAINER_READONLY_CONNECTION_STRING="{connection_string}"
``` 

```bash
export NETWORKS_DATA_CONTAINER_READONLY="{container_name}"   
```

Unlike when running locally (see [vgi_api](../vgi_api/README.md) for where to get values) we can't put these in a `.env` file.

Now we can run the function, which will start the server on port 7071,

```bash
func start
```

To test we can can send a request with an http client,

```bash
http POST :7071/simulate
```
