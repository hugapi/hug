Contributing to hug
=========
Looking for a growing and useful open source Project to contribute to?
Want your contributions to be warmly welcomed and acknowledged?
Want a free project t-shirt to show your a contributor?
Welcome! You have found the right place.

hug is quickly growing and needs awesome contributors like *you* to help the project reach it's full potential.
From reporting issues, writing documentation, implementing new features, fixing bugs, creating logos, to providing additional usage examples - any contribution you can provide will be greatly appreciated and acknowledged.

Getting hug setup for local development
=========
The first step when contributing to any project is getting it setup on your local machine, hug aims to make this as simple as possible.

Account Requirements:
- A valid GitHub account (https://github.com/join)
Base System Requirements:
- Python3.3+
- Python3-venv (included w/ most Python3 installations but some Ubuntu systems require that it be installed separately)
- bash or a bash compatible shell (should be auto-installed on Linux / Mac)
- autoenv - https://github.com/kennethreitz/autoenv (optional)

Once you have verified that you system matches the base requirements you can start get the project working by following these steps:
1. Fork the project on GitHub (https://github.com/timothycrosley/hug/fork).
2. Clone your fork to your local file system:
    `git clone https://github.com/$GITHUB_ACCOUNT/hug.git`
3. `cd hug`
    - If you have autoenv set-up correctly simply press Y and then wait for the environment to be setup for you.
    - If you don't have autoenv set-up run `source .env` to setup the local environment. You will need to run this script everytime you want to work on the project - though it will not cause the entire setup process to re-occur.
4. run `test` to verify your everything is setup correctly, if the tests all pass you have succesfully setup hug for local development! If not you can ask for help diagnosing the error here: https://gitter.im/timothycrosley/hug.

Making a contribution
=========
Congrats! Your now ready to make a contribution! Use the following as a guide to help you reach a succefull pull-request:

1. Check the issues page on github to see if the task you want to complete is listed there https://github.com/timothycrosley/hug/issues.
    - If it's listed there write a comment letting others know you are working on it.
    - If it's not listed in github issues go ahead and log a new issue and then add a comment letting everyone know you have it under control.
        - If you're not sure if it's something that is good for main hug project and want immediate feedback you can discuss it here: https://gitter.im/timothycrosley/hug.
2. Create an issue branch for your local work `git checkout -b issue/$ISSUE-NUMBER`.
3. Do your magic here.
4. Run `clean` to automatically sort your imports according to pep-8 guidlines.
5. Ensure your code matches hug's latest coding standards defined here: https://github.com/timothycrosley/hug/blob/develop/CODING_STANDARD.md.
7. Submit a pull request to the main project repository via GitHub.

Thanks for the contribution! It will quickly get reviewed, and once accepted will result in your name being added to the ACKNOWLEDGEMENTS.md list :).

Getting a free t-shirt
=========
Once you have finished contributing to the project send your mailing address to timothy.crosley@gmail.com, with the title Hug Shirt for @$GITHUB_USER_NAME.
When the project has reached 100 contributers I will be sending every one of the original hundred contributers a t-shirt to commemorate their awesome work.

Thank you!
=========
I can not tell you how thankful I am for the hard work done by hug contributers like you. hug could not be the exciting and useful framework it is today without your help.

Thank you!

~Timothy Crosley
