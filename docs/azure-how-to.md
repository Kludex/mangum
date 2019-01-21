# How to deploy an ASGI app to Azure

This guide will explain how to deploy a basic ASGI application to Azure Functions. There is also an [official guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-python) that explains much of the same information.

The complete example project is available [here](https://github.com/erm/azure-functions-python-asgi-example).

## Requirements 

- Python 3.6
- [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#v2)
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
- A terminal and a browser

### Step 1 - Create the function app in Azure

In the Azure portal, click **Create a Resource** to display the app marketplace, then select **Serverless Function App** to begin.

<img src="https://raw.githubusercontent.com/erm/mangum/master/images/step-1-azure-howto.png" alt="step-1" class="inline"/>

Enter a name for the app function, this should automatically populate a few other inputs as well. The important fields for the purposes of this guide are listed below:

- OS: **Linux (Preview)**
- Publish: **Code**
- Runtime Stack: **Python**
- Hosting Plan: **Consumption Plan**

<img src="https://raw.githubusercontent.com/erm/mangum/master/images/step-2-azure-howto.png" alt="step-2" class="inline"/>

After the form is submitted the deployment process will begin. A successful deployment notification should appear in the Azure portal once complete. The rest of the guide will be in the command-line.

## Step 2 - Setup the local function environment

The [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#v2) are required to continue, they may be installed using npm:

`npm install -g azure-functions-core-tools`

An active Python 3.6 virtual environment must be running to run Python function apps. Assuming Python 3.6 is in the system path, enter the following:

```
python3.6 -m venv venv
. venv/bin/activate
```


## Step 3 - Configure the local Python project

Run the following to create a local project:

```
func init
```

Select the option for Python and it will begin installing some packages. Once completed, run the next command to select a template:

```
func new
```

Then select the option for `HTTP Trigger`, this template will be used for the HTTP example. This example uses the default trigger name, `HttpTrigger`. 

After selecting the template, run the following command to test the default project:

```
func start
```

then visit the URL displayed in the terminal, e.g. http://localhost:7071/api/HttpTrigger.

## Step 4 - Implement a basic ASGI application


Install Mangum from pip:

`pip install mangum`

This will provide a handler method that adapts the Azure Function request events into requests that an ASGI app can understand.

In the current project folder, open the file located at `<project name>/HttpTrigger/__init__.py` in an editor. The default app code will look something like this:

```python
import logging

import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello {name}!")
    else:
        return func.HttpResponse(
             "Please pass a name on the query string or in the request body",
             status_code=400
        )
```


Replace this completely with the following and save:

```python
import logging
import azure.functions as func
from mangum.handlers.azure import azure_handler


class App:
    def __init__(self, scope) -> None:
        self.scope = scope

    async def __call__(self, receive, send) -> None:
        message = await receive()
        if message["type"] == "http.request":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Hello!"})


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")
    return azure_handler(App, req)
```

This is a basic ASGI app example that uses the `azure_handler` that executes the ASGI HTTP request-response cycle. Run the app again with the following command to see the new output:

```
func start
```

If all worked correctly, then it `Hello!` should appear at the browser endpoint.

## Step 5 - Deploy the ASGI app function

Before deploying, one more thing needs to be done, include `mangum` in the `requirements.txt` file and save. This will be necessary to install the requirement in app function, e.g.:

Next run the following command using the app name defined in the app creation form to publish the local Python project, e.g. for a project named "mangum":

`func azure functionapp publish mangum`

This will begin the upload process, the terminal will display something like:

```
Preparing archive...
Uploading 72.39 MB [################################################################]
Upload completed successfully.
Deployment completed successfully.
Syncing triggers...
Functions in mangum:
    HttpTrigger - [httpTrigger]
        Invoke url: https://mangum.azurewebsites.net/api/httptrigger?code=x
```

Then visiting the invoke url should display the same `Hello!` response that appeared in the local test.

**Reminder**: Mangum is a new project and in an unstable/experimental state and may change a lot for the time being.
