# Contributing to Open Study Room website

Thank you for your interest in helping OSR!

This project, as all of the OSR community, grows through the gifts of energy and time of many people.
You are apparently considering giving some of yours, and that is much appreciated!

![cho_hug](https://cdn.discordapp.com/attachments/430062036903395329/444192620504416268/WroCzKKKj7o.png)

## Code of conduct
As a community we like to maintain some simple good-manners rules so everyone can get along together.
We call it our code of conduct and you can find it [here](https://openstudyroom.org/code-conduct/).
As this project is part of OSR, we will ask you to respect it in your issues, PR or code comment.

## Reach us on Discord!
We are an active online community and we mostly hang around discord.
If you are interested in our code, we would be happy to talk with you.
If you have any questions about the code, or want to talk with us for any reason, feel free to meet us [there](https://discord.gg/7sbMHyC).

## I see a problem; how do I report it?
We manage bug reports as GitHub issues.

If you spot a bug, please make sure the issue is not already opened in our [issue list](https://github.com/climu/openstudyroom/issues?q=is%3Aissue+is%3Aopen+label%3Abug).
If not, you can create a new issue.
Explain the problem and include additional details to help maintainers reproduce the problem:
* Use a clear and descriptive title for the issue to identify the problem.
* Describe the exact steps to reproduce the problem with as much detail as possible: What url you are at, whether you are logged in, the browser you are using, your OS and type of device (computer, tablet, phone), etc.

## I have an idea; how do I suggest it?
We also manage enhancement suggestions as GitHub issues.
Again, make sure this idea hasn't been raised before in our [issue list](https://github.com/climu/openstudyroom/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement).

## I can code; how do I participate?

Definitely join us in [Discord](https://discord.gg/7sbMHyC) first.

If you have any trouble getting started, ask for help there.

### Fork and clone the repo and set up a local development environment
You'll need to [fork](https://help.github.com/articles/fork-a-repo/) the repository to your own github account, [clone](https://help.github.com/articles/cloning-a-repository/) it to your machine, and get it running locally.
You will find all of the information you need to get started in [this tutorial](/docs/getting_started.md).

You should be running the project locally with test data in less than 10 minutes.

### What branch to work on?
`master` is what is in production.
`dev` is where most development happens.

As long as you are working in a [fork](https://help.github.com/articles/fork-a-repo/) of the repository, it doesn't matter too much which branch you work on.
Submit [pull requests](https://help.github.com/articles/creating-a-pull-request/) to the `dev` branch.

### Code quality
Your code should pass pylint test.
You can run it with the command `pylint community fixtures fullcalendar home league openstudyroom search wgo manage.py`
or let TravisCI run it automatically when you create the pull request.

## I speak another language; how can I help?

Brilliant! You'll find instructions for contributing translations [here](/docs/translation.md)