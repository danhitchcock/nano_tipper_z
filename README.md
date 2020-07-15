# Nano Tipper
 is a reddit tipping service to easily give Nano to your favorite redditors! [Nano](https://nano.org) is a fast and feeless cryptocurrency that can be traded at numerous exchanges. Before using Nano Tipper, please take a look at the [Terms of Service](https://github.com/danhitchcock/nano_tipper_z#terms-of-service)
### To get started with Nano Tipper, either:
A) **Create an account** by [sending a message](https://reddit.com/message/compose/?to=nano_tipper&subject=command&message=create) to /u/nano_tipper with 'create' or 'register' in the message body. You will receive a Nano address, to which you can add Nano\*. You will receive a 0.001 Nano tip for registering! Also, try any of the faucets at [Nano Links](https://nanolinks.info/#faucets-free-nano) (\**Nano Tipper is in early beta! Only send small amounts of Nano*.)
\-or-
B) **Receive a Nano tip** from a fellow redditor, and you will automatically have an account made! be sure to activate it afterwards by [sending a message](https://reddit.com/message/compose/?to=nano_tipper&subject=command&message=create) to /u/nano_tipper.
Once you have funds in your account, you can tip other redditors, or send to nano address via PM to /u/nano_tipper.
# Comment Replies:
Nano Tipper is intended for tipping on reddit posts and replies. On any [tracked subreddit](https://www.reddit.com/r/nano_tipper/comments/hrvr6o/nano_tipper_status/) you can tip and type a message like:

    !ntip 0.01 This is great!

This will tip a redditor 0.01 Nano. !ntip <amount> must be the first thing in your message OR the last thing. Such, this is also a valid tip:

    This is great! !ntip 0.01

Or from anywhere on reddit, you can tip a commenter by:

    /u/nano_tipper 0.01 This is great!
   
or

    This is great! /u/nano_tipper 0.01

Even specify a currency!

    !ntip 1USD Enjoy a dollar!

If the subreddit is a [friendly subreddit](https://www.reddit.com/r/nano_tipper/comments/hrvr6o/nano_tipper_status/) (which correlates to [tracked subreddit](https://www.reddit.com/r/nano_tipper/comments/hrvr6o/nano_tipper_status/)), the bot will repsond with a message. If the subreddit is not friendly, a PM will be sent to both the sender and the recipient.

### NEW!

    !nanocenter <amount> <project>

such as

    !nanocenter 1 unity
    
for a list of NanoCenter projects, see the PM commands below.
    
# Private Messages

Nano Tipper also works by PM. [Send a message](https://reddit.com/message/compose/?to=nano_tipper&subject=command&message=type_command_here) to /u/nano_tipper for a variety of actions.

To send 0.1 Nano to zily88, include this text in the message body:

    send 0.1 /u/zily88
-or-

    send 0.1 zily88

To send 0.1 Nano to xrb\_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd, include this text in the message body:

    send 0.1 xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd

or send all your balance:

    send all xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd

There are many other commands.

```
'balance' or 'address' - Retrieve your account balance. Includes both pocketed and unpocketed transactions
'create' - Create a new account if one does not exist
'help' - Get this help message
'history <optional: number of records>' - Retrieves tipbot commands. Default 10, maximum is 50.
'minimum <amount>' - (default 0.0001) Sets a minimum amount for receiving tips
'send <amount or all, optional: Currency> <user/address>' - Send Nano to a reddit user or an address
'silence <yes/no>' - (default 'no') Prevents the bot from sending you tip notifications or tagging in posts
'percentage <percent>' - (default 10 percent) Sets a percentage of returned tips to donate to TipBot development
'projects' - Retrives a list of NanoCenter donation projects
'subreddit <subreddit> <'activate'/'deactivate'> <option>' - Subreddit Moderator Controls - Enabled Tipping on Your Sub (`silent`, `minimal`, `full`)
'withdraw <amount or all> <user/address>' - Same as send
```
### Control TipBot Behavior On Your Subreddit
If you are a moderator of a subreddit, and would like to tipping to your sub, use the `subreddit` command. For example, for me to activate tipping on my /r/nano_tipper subreddit, I send a PM to the bot saying:

`subreddit nano_tipper activate`

This will allow the bot to look for !ntip commands and respond to posts. 
-or- If I don't want the bot to respond, but still want tips:

`subreddit nano_tipper activate silent`

-or- for a cleaner tipbot response:

`subreddit nano_tipper activate minimal`

To deactivate, simply PM

`subreddit nano_tipper deactivate`

### Here's a few other great links:
[Nano Tipper Subreddit](https://reddit.com/r/nano_tipper) -- Post any questions about Nano Tipper
[Nano Tipper GitHub](https://github.com/danhitchcock/nano_tipper_z) -- This software is open source!
[Nano Tipper Wiki](https://www.reddit.com/r/nano_tipper/wiki) -- The Subreddit Wiki
[Nano Currency](https://nano.org) -- The Official Nano website
[Nano Links](https://nanolinks.info) -- has numerous useful links to get to using Nano!
[Nano Subreddit](https://www.reddit.com/r/nanocurrency) -- The official Nano Subreddit

# Terms of Service
* Don't keep a lot of Nano in your Nano Tip Bot account
* You accept the risks of using this Tip Bot--I won't steal your Nanos, but they might be lost at any point, and I'm under no obligation to replace them. Don't put in more than you're willing to lose.
* If your account is inactive for more than 3 years, and no meaningful attempt has been made to reach me, the Nanos in your account will be forfeited and I am under no obligation to return them. Why did I write this? Because the tip bot is not a lifelong custodian service -- I don't want people reaching out to me after 20 years for their .032 Nanos the left on the tip bot. I don't want to have to keep the  database with me the rest of my life. After your three years, if the bot is still running, your Nanos will almost certainly be available to you.
* Don't submit more than 5 requests every 30 seconds. The bot will ignore any commands you issue until 30 seconds have passed.
* I can change the Terms of Service at any time.

# FAQ
## Why does the message have to start or end with !nano_tip <amount>?
This is to prevent unintentional tips! If the program simply scanned the entire comment, a user might accidentally quote someone else's tip command in a response. In the future I might change this, but for now it's the best way to ensure the program behaves as expected.

## Are my funds safe?
**NO! Unless you and you alone control your private keys, your funds are never safe!** Please don't keep more than a few Nanos on the tipbot at any time! While I'm not going to steal your Nanos, this program is in early beta testing and weird things could happen, including lost Nanos! **Use at your own risk!** (sorry for all the exclamation marks)

## I sent a tip to the wrong address. Can I get it back?
If the address isn't affiliated with a Redditor, **No.** I only have private keys for redditors, not for addresses. If you send Nano to Binance for example, I cannot retrieve it.

## I sent a tip to the wrong redditor. Can I get it back?
You basically gave a stranger a dollar, and I have no control over that. Yes, I technically control the private keys, but I really don't want to start manually making unauthorized transactions on people's accounts. If the stranger is a redditor and doesn't activate their account, you will get your tip back in 30 days. If they *do* activate their account, it's theirs. You can try asking them for it back.

## Have you implemented any spam prevention for your bot?
Users are allowed 5 requests every 30 seconds. If you do more than that, the bot ignores you until 30 seconds have passed.

## I tried to send a tip, but received no response. Did it go through?
Probably not. It's most likely the bot was temporarily disconnected. If a command is issued while the bot is offline, the command will not be seen. If no response is received from the bot after a few minutes, send a message to the bot with the text 'history'. If you get a response and the tip isn't in your history, that means it wasn't seen. If you don't get a response, the bot is probably still offline. Try again in a few minutes.

## I found a bug or I have a concern. Question Mark?
Send /u/zily88 a PM on reddit, or post on https://reddit.com/r/nano_tipper

# Error Codes
If a reddit tip is a reply to a reply, it's better to keep a short message with an error code.
* 100 - You do\ not have an account -- Create an account by typing 'create' or by receiving a tip from another redditor.
* 110 - You must specify an amount and a user, e.g. `send 1 nano_tipper`.
* 120 - Could not read the tip amount -- use either a number or the word 'all'.
* 130 - Tip amount is below program minimum -- This is to prevent spamming other redditors.
* 140 - If using currency conversion, make sure there is no space. Example: `!ntip 0.5USD`.
* 150 - You are likely attempting to tip in an unfamiliar sub. The minimum is 1 Nano.
* 160 - You have insufficient funds.
* 180 - Tip amount is below recipients specified tip minimum.
* 200 - Please specify a Nanocenter project, e.g. `nanocenter 1 reddit_tipbot`.
* 210 - The Nanocenter project you attempted to donate to does not exist.
