# How To Contribute?

## Table of Contents
- [Overview](#id-section1)
- [Standard contribution process](#id-section2)
- [Mandatory style checks](#id-section3)
- [Mandatory unit tests and test runs](#id-section4)


<div id='id-section1'/>

## Overview
This document explains, how to contribute to project validation-app-engine.
If you want to contribute to a project validation-app-engine and make it better, your help is very welcome.
validation-app-engine follows standard GitHub contribution process.
Along with that this also recommends standard conding styles and unit tests.

<div id='id-section2'/>

## Standard contribution process

For contribution, validation-app-engine is following standard GitHub contribution process.
We strongly recommend to follow the github contribution process from github official documents.

https://git-scm.com/book/en/v2/GitHub-Contributing-to-a-Project

However, few basic steps are given here which should be followed -

    #. New github 'Issue' must be opened for any new change/feature in the project.
    #. Core Reviewers of the project will review the issue and approve it.
    #. Once its approved, one will follow below detailed steps for contributions.
    #. Create a fork of the validation-app-engine on Github.
    #. Clone the fork on your local machine.
    #. Remote repo on Github is called origin.
    #. Add the original repository as a remote called upstream.
    #. Create a new branch (from develop if it exists, else from master) to work on.
    #. Implement/fix your feature, comment your code.
    #. Follow the code style of the project.
    #. Write unit test for your feature/fix.
    #. Run unit test for entire suite.
    #. Add or change the documentation as needed.
    #. Squash your commits into a single commit with git's interactive rebase.
    #. Push your branch to your fork on Github, the remote origin.
    #. From your fork open a pull request in the correct branch.
    #. Target the project's develop branch if there is one, else go for master.
    #. If the maintainer requests further changes just push them to your branch.
    #. The PR will be updated automatically.
    #. Once the pull request is approved and merged you can pull the changes
       from upstream to your local repo.

<div id='id-section3'/>

## Mandatory style checks

After coding is done, python coding style checks should also be run and verified for success.

    $ tox -epep8

<div id='id-section4'/>

## Mandatory unit tests

After adding or updating code, contributor must write or update unit tests.
All unit tests are written under directory - validation-app-engine/axon/tests.
Newly added unit tests or updated unit tests must be run and verified for success using tox.

    How to run unit tests using tox::

        $ tox -epy27
        $ tox -epy35