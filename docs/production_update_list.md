You are considering using a copy of OSR website on production to manage your (online) go community? That's great!

There are few things you might like to change.

This list is here to help you do so.

## The html

It's very likely you will want to adapt some html of the website.

Some pages are created and rendered using the [Wagtail](https://wagtail.io/) Content Managment System. For instance our Faq, code of conduct and all the blog posts. Those pages will be easy to create and require no coding effort.

Other pages use the Django [template system](https://docs.djangoproject.com/en/2.1/topics/templates/) to render the html. You can find those in the templates folder of every app.

The front page might be the more important to change and can be found in the home app [here](/home/templates/home/home_page.html).

## The CSS

Our CSS is in this [static folder](/openstudyroom/static/css).

We are a using a custom bootstrap3 file and some tweaks in [openstudyroom.css](/openstudyroom/static/css/openstudyroom.css). 

You just have to change the bootstrap file to another bootstrap3 css file and it should adapt the look of the website everywhere. You can find free bootstrap theme [here](https://bootswatch.com/3/) for instance.

Of course you can also choose to change css more radically and not use bootstrap at all. Then you will have to adapt every template so it works fine.

## Discord webhooks

We are sending messages on discord whenever on 3 events:
- A user is accepted as a new member: [here](https://github.com/climu/openstudyroom/blob/586b3d446de654ecbe63ba3b5e33b267a3f10718/league/views.py#L717-L736)
- A new forum post is being created: [here](https://github.com/climu/openstudyroom/blob/586b3d446de654ecbe63ba3b5e33b267a3f10718/home/models.py#L233-L273)
- A new blog post is being created: [here](https://github.com/climu/openstudyroom/blob/586b3d446de654ecbe63ba3b5e33b267a3f10718/home/models.py#L198-L230)

As you can see we are reading the discord hook url in files such as `/etc/discord_welcome_hook_url.txt`.

If your community has a discord server, you can use those tools by having urls in the  mentioned files. Otherwise, I am afraid this part of the code will return some errors as they are. Either you remove it or we clean it so it pass if it doesn't find the files.

## KGS room

We connect to KGS OSR room to see who is online and update their rank. This happens [here](https://github.com/climu/openstudyroom/blob/586b3d446de654ecbe63ba3b5e33b267a3f10718/league/views.py#L72).

Just change the `m['channelId'] == 3627409` to your KGS room channelId if you have one.
