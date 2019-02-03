# Open Study Room

[Open Study Room (OSR)](https://openstudyroom.org/) is a community of go/baduk/weiqi players who share, build and organize knowledge, opportunities and resources for learning, studying and playing Go online as part of a thriving worldwide community.

You can always meet us in our [discord server](https://discord.gg/b7meDjX).

# Our website
This is the code of our website that runs at [openstudyroom.org](http://openstudyroom.org).

This website is written in python and powered by the [django framework](https://www.djangoproject.com/).

The project is under GNU GPL 3.

You are welcome to [help us improve it](/CONTRIBUTING.md) or [use it as the base for your own go community website](/docs/production_update_list.md).

It comes with the folowing tools:

## A CMS
To manage the content, we use the [wagtail](https://wagtail.io/) CMS along with the [puput](https://github.com/APSL/puput) blogging app.

The models and templates of this app can be found in the `home` folder.

## A forum
The forum is powered by [machina](https://github.com/ellmetha/django-machina) and uses [mistune](https://github.com/lepture/mistune) for markdown formating.

Custom template forum base template in  [openstudyroom/templates/boardbase.html](/openstudyroom/templates/board_base.html).

## A league app
Allow hosting go leagues where games are played on the KGS or OGS go server. A cron job can get games automatically from those servers.

Note that the auth model `league.models.User ` is in here.

The scraper() function inside `league.views` is run by cron every 5 mins.

It's all under the [league](/league) folder.

## A tournament app
Allow hosting go tournaments. Games must be uploaded manually by admins.

## A calendar and game planning tools
Allow admins to manage calendar events and users to [plan games](https://openstudyroom.org/calendar/help/).

The client side is rendered by the js [fullcalendar](https://fullcalendar.io/) library.

## Js goodies
### [gmt] tag
[This](/openstudyroom/static/js/openstudyroom.js) js will replace every  `[gmt]YYYY/MM/DD HH:mm[/gmt]` to the locale datetime in the user timezone. Example output in french "dimanche 11 novembre 2018 19:00 (Europe/Paris)".

It is loaded on all `.rich-text` elements [here](https://github.com/climu/openstudyroom/blob/586b3d446de654ecbe63ba3b5e33b267a3f10718/openstudyroom/templates/base.html#L143-L144) and in the forum `.post` elements [here](https://github.com/climu/openstudyroom/blob/586b3d446de654ecbe63ba3b5e33b267a3f10718/openstudyroom/templates/board_base.html#L156-L157).

### [goban] tag
This [js](/wgo/static/wgo/shortcode.js) allow to replace `[goban url="url/of/the/url"]some interactive comments[/goban]` to a go board using the [wgo.js](http://wgo.waltheri.net/) library.

It's loaded on the forum `.post-content` elements [here](https://github.com/climu/openstudyroom/blob/586b3d446de654ecbe63ba3b5e33b267a3f10718/openstudyroom/templates/board_base.html#L117-L155).

It's functionalities are documented [here](https://openstudyroom.org/forum/forum/announcements-26/topic/how-to-display-gobans-in-our-forums-77/).


# Contributing:
Have a look at our contributing guidelines [here](/CONTRIBUTING.md).

