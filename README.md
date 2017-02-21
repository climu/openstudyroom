# openstudyroom

This is the code of the website for the Open Study Room kgs community that runs at [openstudyroom.org](http://openstudyroom.org).

This website is written in python and powered by django.

To manage the content, we use the wagtail CMS along with the puput blogging app.

The forum is powered by machina and uses markdown.

The app managing the league is a homemade django app.

The project is under GNU GPL 3.

You can find a How To deploy this locally in our [wiki](https://github.com/climu/openstudyroom/wiki)

# League app
You can find it under the league folder.
The scraper() function inside views.py is run by cron every 5 mins.
