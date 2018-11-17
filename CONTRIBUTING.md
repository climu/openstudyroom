# Contributing to Open Study Room website

Thank you for your will to help OSR!

This project as the all OSR community grows by the energy and time of many people.
You are apparently considering puting some of yours and thats much appreciated.

![cho_hug](https://cdn.discordapp.com/attachments/430062036903395329/444192620504416268/WroCzKKKj7o.png)

## Code of conduct
As a community we like to maintain some simple good maners rules so everyone can get along together.
We call it our code of conduct and you can find it [here](https://openstudyroom.org/code-conduct/).
As this project is part of OSR, we will ask you to respect it in your issues, PR or code comment.

## Reach us on discord!
We are an active online community and we mostly hang around discord. If you are interest in our code, we would be happy to talk with you.
If you have some questions about the code, or want to talk with us for any reason, feel free to meet us [there](https://discord.gg/7sbMHyC).

## I see a problem how do I report it?
We manage bug reports as github issues.

If you spoted a bug, please make sure the issue is not already opened in our [issue list](https://github.com/climu/openstudyroom/issues?q=is%3Aissue+is%3Aopen+label%3Abug).
If not, you can create a new issue. Explain the problem and include additional details to help maintainers reproduce the problem:
* Use a clear and descriptive title for the issue to identify the problem.
* Describe the exact steps which reproduce the problem in as many details as possible: What url are you at, are you loged in, what browser are you using, are you on a mobile.

## I have an idea, how do I suggest it?
We also manage enhancement suggestions as github issues. Again, make sure this idea hasn't been raised before in our [issue list](https://github.com/climu/openstudyroom/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement).

## I can code, how do I participate?

### Set up local testing
First thing to do is to [fork this repository](https://help.github.com/articles/fork-a-repo/).

Then you should set up a local testing environement folowing [this toturial](https://github.com/climu/openstudyroom/wiki/How-to-set-up-local-deployment). This should give you the project locally with testing data in less than 10 minutes.

### What branch to work on?
If you are doing small fix you should work on the `dev` branch and submit Pull Requests to it.

If you are working on a larger feature that might request many commits you should create a dedicated branch to it. If you are unsure about that, feel free to ask us in [discord](https://discord.gg/7sbMHyC).

### Code quality
Your code should pass pylint test. You can run it with the command `pylint community fixtures fullcalendar home league openstudyroom search wgo manage.py`.

Commenting your code as much as possible will help future readers understand it.
