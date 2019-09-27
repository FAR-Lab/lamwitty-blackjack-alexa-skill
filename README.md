# documentation of the alexa skill for the LAMWITTY project

## the account - 
a special account was set up for accessing the alexa developer console.
Here is the frontend part of the skil and the backend part of the skill.

## Frontend:

### about the build - 

I built the front end using the developer console, but it is also possible to configure it using a .json file(or export it)
documentation for it: https://developer.amazon.com/docs/smapi/interaction-model-schema.html
*look for "Interaction model/JSON Editor" tab on the developer console under the "Build" section* 

### what do you need in order to activate the alexa skill's backend - 

all you need to do is:

1. find the **Endpoint** tab on your developer console
2. copy the Skill ID there and in your lambda function configuration you shoul add a triger for alexa skill, and enter that skill ID there
3. copy your lambda function ARN and past it on the Default region option

## Backend:

I am using a lambda function hosted on the lab's AWS account, written  in python 3.7, to host the backend.
- if you want to use any python package or that your code is more than 500 lines(or more than one file) you would want to use the option
of uploading a .zip file, and not using the inline editor, because the editor is not that good, and don't allow packages or long code. 

### using a python package

if you want to add a python package to the function deployment package(for example `ask-sdk` the alexa toolkit) 
you can do it the right way - watch this video: https://www.youtube.com/watch?v=rDbxCeTzw_k
or the fast way (it is ok if your code is not too complex, and only a few packages): pip install them in the fallowing way:
`pip install <package_name> -t .` - the `-t .` tells pip to install it in the current directory.
do it in the folder that the code you are using is in

### uploading a .zip file to lambda

you should zip the package with all of the code that you want the lambda function to run in one zip file, preferably without any subdirectoris,
and use the AWS console (GUI) for uploading it, or (*The prefered way in my opinion*) to configure AWS CLI on your machine, and write a script that automaticly zips and uploads the code to the lambda function.
I wrote down one in .bat script(for windows, using 7zip), called *update_function.bat* - it is better because you might find yourself doing it alot.
AWS CLI - https://aws.amazon.com/cli/


