# 🐮 Cowabunga Cover Bot
Discord bot utilized by my [ROBLOX group](https://www.roblox.com/communities/35565681/Cowabunga-Games#!/about) for user singing submissions to our game. 

We use ROBLOX OpenCloud API to automatically upload sound files, create module scripts inside of our game, and edit our datastores in order to add songs and give rewards to the players who submit covers.

Want to try it out for yourself? Join the Cowabunga Games [discord server](discord.gg/62X7NjxwG4).

## Built with:
- discord.py
- SQLite
- ROBLOX OpenCloud API

## Showcase:
> Users are prompted to submit their song information as well as their audio file.
<img width="900" height="711" alt="image" src="https://github.com/user-attachments/assets/792aa5a5-e1bb-4cdd-903b-03ff1dab1f34" />

> The bot then auto formats the submission into script format and prompts reviewers to accept/edit/reject
<img width="538" height="551" alt="image" src="https://github.com/user-attachments/assets/c5313c3e-5a8c-4967-916d-02574b22edda" />

> On accept, the submitter gets DMed letting them know and OpenCloud API uploads the song, inserts the module into our game, and edits the users data in order to give them rewards.

> On edit, the reviewer can tweak anything wrong with the submission such as capitalization, spelling, etc.

> On reject, the submitter gets DMed letting them know and the reviewer can optionally give the submitter some feedback.
