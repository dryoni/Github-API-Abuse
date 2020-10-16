# Github API Tokens Creator

When opening a new Github account two user interactions are required before the account is created and activated:

- Solve a visual or audio captcha (Requires human interaction)
- Click on the verification link received from Github (Requires having a valid email address)

This script can be used to create multiple Github accounts and an API token for each account, without human interaction, every 70 seconds on average.

By using multiple Github API tokens (created by the script) and alternating the token on each request, it's possible to reach higher request rates and avoid abuse limits as they are looser on IP addresses then on individual tokens.

## Important Note
I've submitted a report to Github's Bug Bounty program that pointed out 4 security issues that allow such behaviour - They don't consider it a security vulnerability, but an abuse issue. They also allowed the release of this script.

There has been no measures taken to prevent the Captcha bypass since then. If they do take any measures, this script will stop working


## Dependencies

- Install the following pip packages:
```bash
pip3 install requests selenium
```

- Get a free AssemblyAI API Token:
  - Generate a one-time email at https://getnada.com/
  - Sign up for a free account at AssemblyAI with the 
one-time Email: https://app.assemblyai.com/login/
  - Save the API Token in an environment variable AAI_TOKEN:
```bash
export AAI_TOKEN="XXXXXXXXXXXX"
```  
  - Look for the verification email, and verify the account


## Usage

```bash
./create_github_tokens.py
```

All new API tokens will be saved in the tokens-list.txt file

## Known issues:
- Only one audio file can be transcribed at a given time with a single API token. Running multiple instances of the script will cause longer subscription time as the excess file will sit in a status of "queued" until the first file is done processing
- AssemblyAI API tokens can be used to transcribe 5 hours of audio file per month, and the average Github audio challenge time is around 6 seconds = 3000 audio challenges per month
- The average time between each transcription attempt is ~ 62 seconds, The AAI token will be suspended after ~ 52 hours of running the script
