const config = require('../config');
const axios = require('axios');

class AICharacter {
    constructor(id, name, role, personality) {
        this.id = id;
        this.name = name;
        this.role = role;
        this.personality = personality || this.getDefaultPersonality();
        this.gameContext = [];
        this.knownInformation = new Map();
    }

    getDefaultPersonality() {
        return "You are a player in a werewolf game. Be strategic but not too obvious. Keep your responses concise and natural.";
    }

    updateGameContext(event) {
        this.gameContext.push(event);
        // Keep only last 10 events to maintain relevant context
        if (this.gameContext.length > 10) {
            this.gameContext.shift();
        }
    }

    addKnownInformation(key, value) {
        this.knownInformation.set(key, value);
    }

    async generateResponse(prompt) {
        const systemPrompt = this.buildSystemPrompt();
        const messages = [
            { role: 'system', content: systemPrompt },
            ...this.gameContext.map(event => ({ role: 'user', content: event })),
            { role: 'user', content: prompt }
        ];

        try {
            const response = await axios.post(config.LLM_API_ENDPOINT, {
                messages,
                temperature: 0.7,
                max_tokens: 150
            }, {
                headers: {
                    'Authorization': `Bearer ${config.LLM_API_KEY}`,
                    'Content-Type': 'application/json'
                }
            });

            return response.data.choices[0].message.content;
        } catch (error) {
            console.error('Error generating AI response:', error);
            return 'I pass my turn.';
        }
    }

    buildSystemPrompt() {
        let prompt = `${this.personality}\n\nYou are playing as ${this.name} and your role is ${this.role}.\n`;
        
        // Add role-specific instructions
        switch (this.role) {
            case 'werewolf':
                prompt += "As a werewolf, you must be deceptive and try to blend in with villagers. Never directly reveal you are a werewolf.";
                break;
            case 'seer':
                prompt += "As a seer, you can reveal information about other players' roles, but be strategic about when to share this information.";
                break;
            case 'witch':
                prompt += "As a witch, you have one save potion and one kill potion. Be careful about revealing your role too early.";
                break;
            case 'hunter':
                prompt += "As a hunter, you can kill one player when you die. Stay low profile until needed.";
                break;
            case 'villager':
                prompt += "As a villager, try to identify the werewolves through careful observation and deduction.";
                break;
        }

        // Add known information
        if (this.knownInformation.size > 0) {
            prompt += "\n\nYou know the following information:\n";
            for (const [key, value] of this.knownInformation) {
                prompt += `- ${key}: ${value}\n`;
            }
        }

        return prompt;
    }

    async makeVoteDecision(livingPlayers, context) {
        const prompt = `Based on the game context, you need to vote for one player to eliminate. Here are the living players: ${livingPlayers.join(', ')}. Who do you vote for? Respond with just the player number.`;
        const response = await this.generateResponse(prompt);
        return parseInt(response.match(/\d+/)?.[0]);
    }

    async makePoliceNomination(context) {
        if (this.role === 'seer') {
            return true; // Seers should always nominate themselves
        }
        
        if (this.role === 'werewolf') {
            // Werewolves have a 50% chance to nominate themselves
            return Math.random() < 0.5;
        }

        // Other roles have a 20% chance to nominate themselves
        return Math.random() < 0.2;
    }

    async makeWerewolfKillDecision(livingPlayers, context) {
        if (this.role !== 'werewolf') return null;

        const prompt = `As a werewolf, you need to choose a player to kill. Here are the living players: ${livingPlayers.join(', ')}. Who do you want to kill? Consider targeting seers and other special roles first. Respond with just the player number.`;
        const response = await this.generateResponse(prompt);
        return parseInt(response.match(/\d+/)?.[0]);
    }

    async makeSeerCheckDecision(livingPlayers, context) {
        if (this.role !== 'seer') return null;

        const prompt = `As a seer, you can check one player's role. Here are the living players: ${livingPlayers.join(', ')}. Who do you want to check? Respond with just the player number.`;
        const response = await this.generateResponse(prompt);
        return parseInt(response.match(/\d+/)?.[0]);
    }

    async makeWitchDecision(killedPlayer, hasAntidote, hasPoison, livingPlayers, context) {
        if (this.role !== 'witch') return { save: false, kill: null };

        let decision = { save: false, kill: null };

        if (hasAntidote && killedPlayer) {
            const savePrompt = `As a witch, player ${killedPlayer} was killed by werewolves. Do you want to use your only antidote to save them? Consider the player's importance and your strategy. Respond with just Yes or No.`;
            const saveResponse = await this.generateResponse(savePrompt);
            decision.save = saveResponse.toLowerCase().includes('yes');
        }

        if (hasPoison) {
            const killPrompt = `As a witch, you can use your poison to kill one player. Here are the living players: ${livingPlayers.join(', ')}. Do you want to use your poison? If yes, respond with the player number. If no, respond with No.`;
            const killResponse = await this.generateResponse(killPrompt);
            const killTarget = parseInt(killResponse.match(/\d+/)?.[0]);
            if (killTarget) decision.kill = killTarget;
        }

        return decision;
    }

    async makeHunterKillDecision(livingPlayers, context) {
        if (this.role !== 'hunter') return null;

        const prompt = `As a hunter, you are dying and can take one player with you. Here are the living players: ${livingPlayers.join(', ')}. Who do you want to kill? Consider who you suspect is a werewolf. Respond with just the player number.`;
        const response = await this.generateResponse(prompt);
        return parseInt(response.match(/\d+/)?.[0]);
    }
}

module.exports = AICharacter; 