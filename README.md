# Nano Tipper Z


**Nano Tipper Z** is a reddit tipping service to easily give Nano to your favorite redditors!
[Nano currency](http://www.nano.org) is one of a kind -- feeless and nearly instant transactions. 
This allows for a few unique features for the tipbot:
* Every transaction is on chain! View the hashes on the block explorer http://www.nanode.co
* Every account is a full featured (albeit not secure) wallet--you will soon be able to change your rep!
* You can request your private keys or a new address! (Still on the fence, but *soon*)

In addition to those, there are other great features
* Set a tip minimum to prevent spam or annoying cheapskates
* Silence - Turn off tip notifications. You will still receive tips, but won't be tagged or messaged by the bot.
* Set your account to 'auto-receive' transactions (default on)
 
Features to be added:
* 30 day return if an account remains unactivated -- activation is easy! Just perform *any* command
* Custom footers and response behavior for subreddits
* Tipping a currency equivalent in Nano -- USD/EUR/YEN and a few others

**THIS TIP BOT IS NOT:**
* a stable secure wallet
* a custodian service
* a great place to keep your Nano

Feel free to test any functionality at https://reddit.com/r/nano_tipper_z

To get started, either:

A) **Create an account** by sending a message to /u/nano_tipper_z with 'create' in the message body. You will receive a Nano address, to which you can add Nano\*. Try http://nano-faucet.org to receive some free Nano! (\**this project is in early beta! Only send small amounts of Nano*.)

-or-

B) **Receive a Nano tip** from a fellow redditor, and you will automatically have an account made!

Once you have funds in your account, you can tip other redditors, or send to nano address via PM to /u/nano_tipper_z.
# Usage
## Comment Replies:

Nano Tipper Z is intended for tipping on reddit posts and replies.

    !nano_tip <amount>

Watch for spaces. !nano_tip must be the first thing in your message, and it cannot be a part of a reply.

Examples:

Send 0.1 Nano to the parent-comment author:

    !nano_tip 0.1


## Private Messages

Nano Tipper Z also works by PM. Send a message to /u/nano_tipper_z for a variety of actions.

To send 0.1 Nano to zily88, include this text in the message body:

    send 0.1 /u/zily88
    -or-
    send 0.1 zily88

To send 0.1 Nano to xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd, include this text in the message body:

    send 0.1 xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd

To send all your Nano to xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd:

    send all xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd

There are many other PM commands:

    'create' - Create a new account if one does not exist
    'send <amount or all> <user/address>' - Send Nano to a reddit user or an address
    'receive' - Receive all pending transactions (if autoreceive is set to 'no')
    'balance' or 'address' - Retrieve your account balance. Includes both pocketed and unpocketed transactions
    'minimum <amount>' - (default 0.0001) Sets a minimum amount for receiving tips
    'auto_receive <yes/no>' - (default 'yes') Automatically pockets transactions. Checks every 12 seconds
    'silence <yes/no>' - (default 'no') Prevents the bot from sending you tip notifications or tagging in posts 
    'history' - (disabled) Grabs the last 20 records of your account history
    'private_key' - (disabled) Retrieve your account private key
    'new_address' - (disabled) If you feel this address was compromised, create a new account and key
    'help' - Get this help message

# Terms of Service
* Don't keep a lot of Nano in your Nano Tip Bot account
* This program is not-for-profit
* You accept the risks of using this Tip Bot--I won't steal your Nanos, but they might be lost at any point, and under no obligation to replace them. Don't put in more than you're willing to lose.
* Don't submit more than 5 requests every 30 seconds
* I can change the Terms of Service at any time. The only thing I promise is I will return your Nanos if I have posession of them. 

# FAQ
## Why does the message have to start with !nano_tip?
This is to prevent uninentional tips! If the program simply scanned the entire comment, a user might accidently quote someone else's 
tip command in a response.

## Are my funds safe?
**NO! Unless you and you alone control your private keys, your funds are never safe!** Please don't keep more than a few Nanos on the tipbot at any time! While I'm not going to steal your Nanos, this program is in early beta testing and weird things could happen, including lost Nanos! **Use at your own risk!** (sorry for all the exclamation marks)

## I sent a tip to the wrong redditor. Can I get it back?
You basically gave a stranger a dollar, and I have no control over that. Yes, I control the private keys, but I really don't want to start manually making unauthorized transactions on people's accounts. If the stranger doesn't activate their account, you will get your tip back in 30 days. If they *do* activate their account, it's theirs. You can try asking them for it back.

## Have you implemented any spam prevention for your bot?
Users are allowed 5 requests every 30 seconds. If you do more than that, the bot ignores you until 30 seconds have passed.

## I found a bug or I have a concern. Question Mark?
Send /u/zily88 a PM on reddit, or post on https://reddit.com/r/nano_tipper_z
