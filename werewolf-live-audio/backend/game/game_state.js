const { EventEmitter } = require('events');
const config = require('../config');

class GameState extends EventEmitter {
    constructor() {
        super();
        this.players = new Map(); // Map of player ID to player info
        this.roles = new Map(); // Map of player ID to role
        this.isNight = true;
        this.currentDay = 0;
        this.phase = 'waiting'; // waiting, night, day
        this.deadPlayers = new Set();
        this.votes = new Map();
        this.police = null;
        this.currentSpeaker = null;
        this.speakQueue = [];
        this.gameStarted = false;
    }

    addPlayer(playerId, isAI = true, name = null) {
        this.players.set(playerId, {
            id: playerId,
            isAI,
            name: name || `Player ${playerId}`,
            isAlive: true,
            hasSpoken: false
        });
    }

    removePlayer(playerId) {
        this.players.delete(playerId);
        this.roles.delete(playerId);
    }

    assignRoles() {
        const playerIds = Array.from(this.players.keys());
        const numPlayers = playerIds.length;
        
        // Calculate role distribution
        const numWerewolves = Math.ceil(numPlayers / 3);
        const numSeers = numPlayers >= 6 ? 1 : 0;
        const numWitches = numPlayers >= 6 ? 1 : 0;
        const numHunters = numPlayers >= 9 ? 1 : 0;
        const numVillagers = numPlayers - numWerewolves - numSeers - numWitches - numHunters;

        // Create role pool
        const roles = [
            ...Array(numWerewolves).fill('werewolf'),
            ...Array(numVillagers).fill('villager'),
            ...Array(numSeers).fill('seer'),
            ...Array(numWitches).fill('witch'),
            ...Array(numHunters).fill('hunter')
        ];

        // Shuffle roles
        for (let i = roles.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [roles[i], roles[j]] = [roles[j], roles[i]];
        }

        // Assign roles
        playerIds.forEach((playerId, index) => {
            this.roles.set(playerId, roles[index]);
        });
    }

    startGame() {
        if (this.players.size < 3) {
            throw new Error('Not enough players to start the game');
        }

        this.gameStarted = true;
        this.assignRoles();
        this.currentDay = 1;
        this.isNight = false;
        this.phase = 'day';
        this.emit('gameStarted');
        
        // Start with police election
        this.startPoliceElection();
    }

    startPoliceElection() {
        this.phase = 'policeElection';
        this.speakQueue = Array.from(this.players.keys())
            .filter(id => this.players.get(id).isAlive);
        this.emit('policeElectionStarted');
        this.processNextSpeaker();
    }

    startNight() {
        this.isNight = true;
        this.phase = 'night';
        this.emit('nightStarted', this.currentDay);
        
        // Process werewolves first
        this.processWerewolves();
    }

    startDay() {
        this.isNight = false;
        this.phase = 'day';
        this.currentDay++;
        this.emit('dayStarted', this.currentDay);
        
        // Announce deaths and process last words
        this.announceDeaths();
    }

    processWerewolves() {
        const werewolves = Array.from(this.roles.entries())
            .filter(([id, role]) => role === 'werewolf' && this.players.get(id).isAlive)
            .map(([id]) => id);
        
        this.speakQueue = werewolves;
        this.emit('werewolvesPhaseStarted', werewolves);
        this.processNextSpeaker();
    }

    processSeer() {
        const seer = Array.from(this.roles.entries())
            .find(([id, role]) => role === 'seer' && this.players.get(id).isAlive);
        
        if (seer) {
            this.currentSpeaker = seer[0];
            this.emit('seerPhaseStarted', seer[0]);
        } else {
            this.processWitch();
        }
    }

    processWitch() {
        const witch = Array.from(this.roles.entries())
            .find(([id, role]) => role === 'witch' && this.players.get(id).isAlive);
        
        if (witch) {
            this.currentSpeaker = witch[0];
            this.emit('witchPhaseStarted', witch[0]);
        } else {
            this.startDay();
        }
    }

    processNextSpeaker() {
        if (this.speakQueue.length === 0) {
            this.emit('allPlayersSpoken');
            return;
        }

        this.currentSpeaker = this.speakQueue.shift();
        this.emit('nextSpeaker', this.currentSpeaker);
    }

    vote(voterId, targetId) {
        if (!this.players.get(voterId).isAlive) {
            throw new Error('Dead players cannot vote');
        }

        this.votes.set(voterId, targetId);
        this.emit('vote', { voter: voterId, target: targetId });

        // Check if all living players have voted
        const livingPlayers = Array.from(this.players.entries())
            .filter(([_, player]) => player.isAlive)
            .map(([id]) => id);

        if (Array.from(this.votes.keys()).length === livingPlayers.length) {
            this.processVotes();
        }
    }

    processVotes() {
        const voteCount = new Map();
        
        // Count votes
        for (const [_, targetId] of this.votes) {
            voteCount.set(targetId, (voteCount.get(targetId) || 0) + 1);
        }

        // Find player with most votes
        let maxVotes = 0;
        let eliminated = null;
        for (const [targetId, count] of voteCount) {
            if (count > maxVotes) {
                maxVotes = count;
                eliminated = targetId;
            }
        }

        if (eliminated) {
            this.killPlayer(eliminated);
            this.emit('playerEliminated', eliminated);
        }

        this.votes.clear();
        
        // Check game end condition
        if (this.checkGameEnd()) {
            return;
        }

        // Move to next phase
        if (this.isNight) {
            this.processSeer();
        } else {
            this.startNight();
        }
    }

    killPlayer(playerId) {
        const player = this.players.get(playerId);
        if (player) {
            player.isAlive = false;
            this.deadPlayers.add(playerId);
            this.emit('playerDied', playerId);
        }
    }

    checkGameEnd() {
        const livingPlayers = Array.from(this.players.entries())
            .filter(([_, player]) => player.isAlive);
        
        const livingWerewolves = livingPlayers
            .filter(([id]) => this.roles.get(id) === 'werewolf')
            .length;
        
        const livingVillagers = livingPlayers
            .filter(([id]) => this.roles.get(id) !== 'werewolf')
            .length;

        if (livingWerewolves === 0) {
            this.emit('gameEnded', 'villagers');
            return true;
        }

        if (livingVillagers === 0) {
            this.emit('gameEnded', 'werewolves');
            return true;
        }

        return false;
    }

    getPlayerRole(playerId) {
        return this.roles.get(playerId);
    }

    isPlayerAlive(playerId) {
        const player = this.players.get(playerId);
        return player && player.isAlive;
    }
}

module.exports = GameState; 