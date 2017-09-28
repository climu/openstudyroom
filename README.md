# openstudyroom

This is the code of the website for the Open Study Room go/baduk/weiqi community that runs at [openstudyroom.org](http://openstudyroom.org).

This website is written in python and powered by the [django framework](https://www.djangoproject.com/).

To manage the content, we use the [wagtail](https://wagtail.io/) CMS along with the [puput](https://github.com/APSL/puput) blogging app.

The forum is powered by [machina](https://github.com/ellmetha/django-machina) and uses [markdown](https://github.com/trentm/python-markdown2).

The app managing the league is a homemade django app.

The project is under GNU GPL 3.

You can find a How To deploy this locally in our [wiki](https://github.com/climu/openstudyroom/wiki)

# Project structure

### league
That's the main thing. The league app that manage the leagues, players, sgf.

Note that the auth model `league.models.User ` is in here.

The scraper() function inside `league.views` is run by cron every 5 mins.

### home
The wagtail (our CMS) app. You will find definitions and templates of our pages, blog post and such in `home.models`.

### fullcalendar
An homemade app that manage a calendar, public events, and a [game planing tool](https://openstudyroom.org/blog/2017/07/06/game-planing-tool-released-beta-test-needed/).
The client side is rendered by the js [fullcalendar](https://fullcalendar.io/) library.

### community
Allow OSR to host friendly online go community's leagues. See [here](https://openstudyroom.org/community/).
