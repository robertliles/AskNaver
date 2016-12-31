AskNaver
==============

Sublime text plugin to assist Korean-to-English translation. Selected text can be submitted to the [Naver Machine Translation API](https://developers.naver.com/docs/labs/translator); evaluated translation opened in a new pane.

Usage
-----

Requires credentials to authenticate with the machine translation API. Credentials should be stored in directory as `conf-secure.ini` with the following format:

```
[credentials]
client_id = my_client_id
client_secret = my_client_secret
```