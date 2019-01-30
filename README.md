# Nano Tipper Z


**Nano Tipper Z** is a reddit tipping service to easily give Nano to your favorite redditors!
[Nano currency](http://www.nano.org) is one of a kind -- feeless and nearly instant transactions. 
This allows for a few unique features for the tipbot:
* Every transaction is on chain! View the hashes on the block explorer http://www.nanode.co
* Every account is a full featured wallet!
* You can request your private keys or a new address!

A few other nice features (some to be implemented):
* Set a tip minimum to prevent spam or annoying cheapskates
* Set your account to 'auto-receive' transactions
* Turn off notifications. You can still get money, you just won't be informed when you get tipped.

Feel free to test any functionality at https://reddit.com/r/nano_tipper_z

To get started, either:

A) **Create an account** by sending a message to /u/nano_tipper_z with 'create' in the message body. You will receive a Nano address, to which you can add Nano\* (\**this project is in early beta! Only send small amounts of Nano*.)

-or-

B) **Receive a Nano tip** from a fellow redditor, and you will automatically have an account made!

Once you have funds in your account, you can tip other redditors, or send to nano address via PM to /u/nano_tipper_z.
# Usage
## Comment Replies:

Nano Tipper Z is intended for tipping on reddit posts and replies.

    !nano_tip <amount> <(optional) username/address>

Watch for spaces. !nano_tip must be the first thing in your message, and it cannot be a part of a reply.

Examples:

Send 0.1 Nano to the parent-comment author:

    !nano_tip 0.1

Send 0.1 Nano to /u/zily88:

    !nano_tip 0.1 /u/zily88
    -or-
    !nano_tip 0.1 zily88

Send 0.1 Nano to an address:

    !nano_tip 0.1 xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd
    -or-
    !nano_tip 0.1 nano_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd


## Private Messages

Nano Tipper Z also works by PM. Send a message to /u/nano_tipper_z for a variety of actions. Include the command in the body of the text.

To send 0.1 Nano to zily88, include this text in the message body:

    send 0.1 /u/zily88
    -or-
    send 0.1 zily88

To send 0.1 Nano to xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd, include this text in the message body:

    send 0.1 xrb_1ssr4sbop5wnkbkpk7y7ekewie7tygtjgdukm9jq7d1m3j6ocfskwyx77awd

There are many other commands.

    'create' - Create a new account if one does not exist
    'private_key' -  (disabled) Retrieve your account private key
    'new_address' - (disabled) If you feel this address was compromised, create a new account and key
    'send <amount> <user/address> - Send Nano to a reddit user or an address
    'receive' - Receive all pending transactions
    'balance' - Retrieve your account balance. Includes both pocketed and unpocketed transactions
    'minimum <amount>' - (default 0.01) Sets a minimum amount for receiving tips
    'auto_receive <yes/no>' - (default 'yes') Automatically pcokets transactions
    'silence <yes/no>' - (disabled, default 'no') Prevents bot from sending messages, unless specifically requested from user
    'help' - Get this help message\n\n\n