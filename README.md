# Report for Assignment 1

## Project chosen

Name: Hug by Hug API

URL: https://github.com/hugapi/hug/

Number of lines of code and the tool used to count it: 10.8 KLOC - Lizzard

Programming language: Python

## Coverage measurement

### Existing tool

We ran coverage.py ; we tested it within the project root to see what functions needed to be improved and then selected 8 functions to make/enhance tests for.

<img src="readme_img/BEFORE_UNITTESTS.png" alt="COVERAGE BEFORE UNITTESTS" width="200">

### Your own coverage tool

### Individual tests

#### Marwan Amrhar,

---

- `Localrouter.__init__`

Before:

<img src="readme_img/before/localrouterinit_before.png" height="80">

After:

<img src="readme_img/after/localrouterinit_after.png" height="80">

---

- `Localrouter.directives`

Before:

<img src="readme_img/before/localrouterdirectives_before.png" height="80">

After:

<img src="readme_img/after/localrouterdirectives_after.png" height="80">

- Fixed a bug with the use of a deprecated function (numpy.unicode -> numpy.str\_);

#### Sajeed Bouziane,

---

- `Localrouter.validate`

Before:

<img src="readme_img/before/localroutervalidate_before.png" height="80">

After:

<img src="readme_img/after/localroutervalidate_after.png" height="80">

---

- `Localrouter.version`

Before:

<img src="readme_img/before/localrouterversion_before.png" height="80">

After:

<img src="readme_img/after/localrouterversion_after.png" height="80">

#### Ayoub Bouazza,

---

- `Localrouter.__call__`

Before:

<img src="readme_img/before/localroutercall_before.png" height="80">

After:

<img src="readme_img/after/localroutercall_after.png" height="80">

---

- `Router.__init__`

Before:

<img src="readme_img/before/routerinit_before.png" height="50">

After:

<img src="readme_img/after/routerinit_after.png" height="50">

#### Yahia Noeman,

---

- `API.__init__`

Before:

<img src="readme_img/before/apiinit_before.png" height="25">

After:

<img src="readme_img/after/apiinit_after.png" height="25">

---

- `ModuleSingleton.__call__`

Before:

<img src="readme_img/before/modulesingletoncall_before.png" height="40">

After:

<img src="readme_img/after/modulesingletoncall_after.png" height="40">

### Overall

---

This is the overall coverage after implementing our unittests:

<img src="readme_img/AFTER_UNITTESTS.png" alt="COVERAGE AFTER UNITTESTS" width="200">

As we can see the coverage of the files api.py, routing.py have been increased, these also contained the functions that we covered.

## Statement of individual contributions

First we all together did the lizzard count and overall coverage and figured out how to exactly make a unit test and experimented around with Localrouter since we discovered that this was barely/not tested.

Marwan Amrhar:

- Figured out a bug which didn't allow us to run the coverage;
- Figured out how to make unit tests in localrouter and made 2 unit tests in there.

Sajeed Bouziane

- Made 2 more unit tests in localrouter after working together with Marwan;
- Helped set-up the readme file.

Ayoub Bouazza:

- Made a final unit test in localrouter;
- Made a unit test for the initialization of the Router class.

Yahia Nouman

- Made a unit tests for the api.py file which covered the initialization of the api
- Made a unit test for the api.py file which covered singleton module call function.
