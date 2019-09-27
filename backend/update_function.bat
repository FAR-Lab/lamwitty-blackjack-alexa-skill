"C:\Program Files (x86)\7-Zip\7z.exe" a -r function.zip -w .\alexa-lamwitty-blackjack\* -mem=AES256  
aws lambda update-function-code --function-name alexa-lamwitty-blackjack --zip-file fileb://function.zip
