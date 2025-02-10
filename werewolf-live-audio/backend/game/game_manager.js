const GameState = require('./game_state');
const AICharacter = require('./ai_character');
const config = require('../config');
const { EventEmitter } = require('events');

class GameManager extends EventEmitter {
    constructor(connectionHandler) {
        super();
        this.state = new GameState();
        this.aiCharacters = new Map();
        this.connectionHandler = connectionHandler;
        this.setupEventHandlers();
        this.witchPotions = new Map(); // Track witch potions for each witch
    }

    setupEventHandlers() {
        // Game state events
        this.state.on('gameStarted', () => this.handleGameStarted());
        this.state.on('policeElectionStarted', () => this.handlePoliceElectionStarted());
        this.state.on('nightStarted', (day) => this.handleNightStarted(day));
        this.state.on('dayStarted', (day) => this.handleDayStarted(day));
        this.state.on('werewolvesPhaseStarted', (werewolves) => this.handleWerewolvesPhase(werewolves));
        this.state.on('seerPhaseStarted', (seer) => this.handleSeerPhase(seer));
        this.state.on('witchPhaseStarted', (witch) => this.handleWitchPhase(witch));
        this.state.on('nextSpeaker', (playerId) => this.handleNextSpeaker(playerId));
        this.state.on('playerDied', (playerId) => this.handlePlayerDied(playerId));
        this.state.on('playerEliminated', (playerId) => this.handlePlayerEliminated(playerId));
        this.state.on('gameEnded', (winner) => this.handleGameEnded(winner));
    }

    async createAICharacter(id, role) {
        const character = new AICharacter(
            id,
            `Player ${id}`,
            role,
            this.getRandomPersonality()
        );
        this.aiCharacters.set(id, character);
        
        if (role === 'witch') {
            this.witchPotions.set(id, { antidote: true, poison: true });
        }
        
        return character;
    }

    getRandomPersonality() {
        const personalities = [
            "You are cautious and analytical, carefully considering each decision.",
            "You are bold and outspoken, not afraid to voice your suspicions.",
            "You are diplomatic and strategic, building alliances when possible.",
            "You are observant and quiet, speaking only when you have something important to say.",
            "You are charismatic and persuasive, good at influencing others."
        ];
        return personalities[Math.floor(Math.random() * personalities.length)];
    }

    async startGame(humanPlayerId) {
        // Add human player
        this.state.addPlayer(humanPlayerId, false, "Human Player");
        
        // Add AI players (minimum 5 players total)
        const numAIPlayers = Math.max(4, 7 - 1); // -1 for human player
        for (let i = 0; i < numAIPlayers; i++) {
            const aiId = `ai_${i + 1}`;
            this.state.addPlayer(aiId, true);
        }

        // Start the game
        this.state.startGame();
    }

    async handleGameStarted() {
        // Create AI characters with their assigned roles
        for (const [playerId, player] of this.state.players) {
            if (player.isAI) {
                const role = this.state.getPlayerRole(playerId);
                await this.createAICharacter(playerId, role);
            }
        }

        // Announce game start and roles
        await this.speak("Moderator", "Game has started! I will now privately tell each player their role.");
        
        // Tell each player their role
        for (const [playerId, player] of this.state.players) {
            const role = this.state.getPlayerRole(playerId);
            const message = `You are ${player.name}. Your role is ${role}.`;
            await this.speak("Moderator", message, [playerId]);
        }
    }

    async handlePoliceElectionStarted() {
        await this.speak("Moderator", "It's time to elect a police chief. Each player will have a chance to nominate themselves.");
        await this.processPoliceNominations();
    }

    async processPoliceNominations() {
        const livingPlayers = this.getLivingPlayers();
        const nominations = new Map();

        // Ask each living player if they want to nominate themselves
        for (const [playerId, player] of livingPlayers) {
            if (player.isAI) {
                // AI players have a 50% chance to nominate themselves
                if (Math.random() > 0.5) {
                    nominations.set(playerId, player);
                    await this.speak("Moderator", `${player.name} has nominated themselves for police chief.`);
                } else {
                    await this.speak("Moderator", `${player.name} declines to nominate themselves.`);
                }
            } else {
                // For human players, we'll wait for their input
                await this.speak("Moderator", `${player.name}, would you like to nominate yourself for police chief? Please say 'yes' or 'no'.`);
                // The actual nomination will be handled by the human input handler
                // We'll give them 30 seconds to respond
                await new Promise(resolve => setTimeout(resolve, 30000));
            }
        }

        // If no nominations, randomly select a police chief
        if (nominations.size === 0) {
            const randomPlayer = Array.from(livingPlayers.entries())[Math.floor(Math.random() * livingPlayers.size)];
            this.state.policeChief = randomPlayer[0];
            await this.speak("Moderator", `Since no one nominated themselves, ${randomPlayer[1].name} has been randomly selected as police chief.`);
            return;
        }

        // If only one nomination, they become police chief
        if (nominations.size === 1) {
            const [nomineeId, nominee] = nominations.entries().next().value;
            this.state.policeChief = nomineeId;
            await this.speak("Moderator", `${nominee.name} is the only nominee and becomes police chief by default.`);
            return;
        }

        // If multiple nominations, hold a vote
        await this.speak("Moderator", "Multiple players have nominated themselves. We will now hold a vote.");
        const votes = new Map();
        for (const [voterId, voter] of livingPlayers) {
            if (voter.isAI) {
                // AI players randomly vote for one of the nominees
                const nominees = Array.from(nominations.entries());
                const randomNominee = nominees[Math.floor(Math.random() * nominees.length)];
                votes.set(voterId, randomNominee[0]);
                await this.speak("Moderator", `${voter.name} has cast their vote.`);
            } else {
                // For human players, list the nominees and wait for their vote
                const nomineeList = Array.from(nominations.values()).map(p => p.name).join(", ");
                await this.speak("Moderator", `${voter.name}, please vote for one of the following players: ${nomineeList}`);
                // The actual vote will be handled by the human input handler
                // We'll give them 30 seconds to vote
                await new Promise(resolve => setTimeout(resolve, 30000));
            }
        }

        // Count votes and determine winner
        const voteCounts = new Map();
        for (const vote of votes.values()) {
            voteCounts.set(vote, (voteCounts.get(vote) || 0) + 1);
        }

        let maxVotes = 0;
        let winner = null;
        for (const [nomineeId, voteCount] of voteCounts) {
            if (voteCount > maxVotes) {
                maxVotes = voteCount;
                winner = nomineeId;
            }
        }

        this.state.policeChief = winner;
        await this.speak("Moderator", `${livingPlayers.get(winner).name} has been elected as police chief.`);
    }

    async handleNightStarted(day) {
        await this.speak("Moderator", `Night ${day} has fallen. Everyone close your eyes.`);
        // Night phases will be handled by specific event handlers
    }

    async handleDayStarted(day) {
        await this.speak("Moderator", `Day ${day} has begun. Everyone open your eyes.`);
        // Process any deaths from the night
        if (this.state.deadPlayers.size > 0) {
            const deadPlayers = Array.from(this.state.deadPlayers)
                .map(id => this.state.players.get(id).name)
                .join(", ");
            await this.speak("Moderator", `Last night, ${deadPlayers} were killed.`);
        } else {
            await this.speak("Moderator", "No one died last night.");
        }
    }

    async handleWerewolvesPhase(werewolves) {
        await this.speak("Moderator", "Werewolves, open your eyes and choose your victim.", werewolves);
        
        // Get votes from each werewolf
        const votes = new Map();
        for (const werewolfId of werewolves) {
            const character = this.aiCharacters.get(werewolfId);
            if (character) {
                const livingPlayers = this.getLivingPlayers()
                    .filter(p => !werewolves.includes(p.id));
                const target = await character.makeWerewolfKillDecision(
                    livingPlayers.map(p => p.name),
                    this.getGameContext()
                );
                if (target) votes.set(werewolfId, target);
            }
        }

        // Process werewolf votes
        const voteCounts = new Map();
        for (const target of votes.values()) {
            voteCounts.set(target, (voteCounts.get(target) || 0) + 1);
        }

        // Find the target with most votes
        let maxVotes = 0;
        let victim = null;
        for (const [target, count] of voteCounts) {
            if (count > maxVotes) {
                maxVotes = count;
                victim = target;
            }
        }

        if (victim) {
            this.state.killPlayer(victim);
            await this.speak("Moderator", "The werewolves have made their choice.", werewolves);
        }
    }

    async handleSeerPhase(seerId) {
        const character = this.aiCharacters.get(seerId);
        if (!character) return;

        await this.speak("Moderator", "Seer, open your eyes and choose a player to investigate.", [seerId]);
        
        const livingPlayers = this.getLivingPlayers()
            .filter(p => p.id !== seerId);
        const target = await character.makeSeerCheckDecision(
            livingPlayers.map(p => p.name),
            this.getGameContext()
        );

        if (target) {
            const targetRole = this.state.getPlayerRole(target);
            character.addKnownInformation(
                `Player ${target} Role`,
                targetRole
            );
            await this.speak("Moderator", `Player ${target} is a ${targetRole}.`, [seerId]);
        }

        await this.speak("Moderator", "Seer, close your eyes.", [seerId]);
    }

    async handleWitchPhase(witchId) {
        const character = this.aiCharacters.get(witchId);
        if (!character) return;

        const potions = this.witchPotions.get(witchId);
        if (!potions) return;

        await this.speak("Moderator", "Witch, open your eyes.", [witchId]);

        // Handle antidote
        if (potions.antidote && this.state.deadPlayers.size > 0) {
            const killedPlayer = Array.from(this.state.deadPlayers)[0];
            const livingPlayers = this.getLivingPlayers();
            const decision = await character.makeWitchDecision(
                killedPlayer,
                true,
                potions.poison,
                livingPlayers.map(p => p.name),
                this.getGameContext()
            );

            if (decision.save) {
                this.state.deadPlayers.delete(killedPlayer);
                potions.antidote = false;
                await this.speak("Moderator", "The witch has used the antidote.", [witchId]);
            }

            if (decision.kill && potions.poison) {
                this.state.killPlayer(decision.kill);
                potions.poison = false;
                await this.speak("Moderator", "The witch has used the poison.", [witchId]);
            }
        }

        await this.speak("Moderator", "Witch, close your eyes.", [witchId]);
    }

    async handleNextSpeaker(playerId) {
        const player = this.state.players.get(playerId);
        if (!player) return;

        if (player.isAI) {
            const character = this.aiCharacters.get(playerId);
            if (character) {
                const response = await character.generateResponse(
                    "It's your turn to speak. Share your thoughts about who might be a werewolf."
                );
                await this.speak(playerId, response);
            }
        } else {
            // For human player, the frontend will handle their turn
            await this.speak("Moderator", "It's your turn to speak.");
            // Wait for human input...
        }
    }

    async handlePlayerDied(playerId) {
        const player = this.state.players.get(playerId);
        if (!player) return;

        // Handle hunter's ability
        if (this.state.getPlayerRole(playerId) === 'hunter') {
            const character = this.aiCharacters.get(playerId);
            if (character) {
                const livingPlayers = this.getLivingPlayers();
                const target = await character.makeHunterKillDecision(
                    livingPlayers.map(p => p.name),
                    this.getGameContext()
                );
                if (target) {
                    this.state.killPlayer(target);
                    await this.speak("Moderator", `The hunter has chosen to take ${this.state.players.get(target).name} with them.`);
                }
            }
        }
    }

    async handlePlayerEliminated(playerId) {
        const player = this.state.players.get(playerId);
        if (!player) return;

        await this.speak("Moderator", `${player.name} has been eliminated. They were a ${this.state.getPlayerRole(playerId)}.`);
    }

    async handleGameEnded(winner) {
        await this.speak("Moderator", `Game Over! The ${winner} have won!`);
        
        // Reveal all roles
        for (const [playerId, player] of this.state.players) {
            const role = this.state.getPlayerRole(playerId);
            await this.speak("Moderator", `${player.name} was a ${role}.`);
        }
    }

    getLivingPlayers() {
        // Return a new Map containing only living players
        return new Map(
            Array.from(this.state.players)
                .filter(([_, player]) => player.isAlive)
        );
    }

    getGameContext() {
        return {
            day: this.state.currentDay,
            isNight: this.state.isNight,
            phase: this.state.phase,
            livingPlayers: Array.from(this.getLivingPlayers().values())
        };
    }

    async speak(speaker, message, targetPlayers = null) {
        try {
            // Add speaker information to the message
            const speakerInfo = {
                type: 'speaker_info',
                speaker: speaker,
                name: speaker === 'Moderator' ? 'Moderator' : this.state.players.get(speaker)?.name,
                role: speaker === 'Moderator' ? 'Moderator' : this.state.getPlayerRole(speaker)
            };
            
            // Send speaker info first
            this.connectionHandler.ws.send(JSON.stringify(speakerInfo));

            // Send game log message
            const gameLogMessage = {
                type: 'game_log',
                speaker: speakerInfo.name,
                message: message,
                timestamp: new Date().toISOString(),
                isPrivate: targetPlayers !== null
            };
            this.connectionHandler.ws.send(JSON.stringify(gameLogMessage));
            
            // Skip TTS for initial game rules and role announcements
            const skipTTSPatterns = [
                /Game has started/i,
                /You are .+\. Your role is/i,
                /It's time to elect a police chief/i,
                /Each player will have a chance to nominate themselves/i
            ];
            
            const shouldSkipTTS = skipTTSPatterns.some(pattern => pattern.test(message));
            
            // Only send TTS for gameplay messages
            if (!shouldSkipTTS) {
                await this.connectionHandler.synthesizeAndStreamAudio(message);
            }
            
            // Update AI characters' context
            for (const character of this.aiCharacters.values()) {
                if (!targetPlayers || targetPlayers.includes(character.id)) {
                    character.updateGameContext(`${speaker}: ${message}`);
                }
            }
        } catch (error) {
            console.error('Error in speak:', error);
        }
    }

    // Handle human player input
    async handleHumanInput(playerId, message) {
        if (this.state.currentSpeaker === playerId) {
            // Process the human player's message
            await this.speak(playerId, message);
            this.state.processNextSpeaker();
        }
    }
}

module.exports = GameManager; 