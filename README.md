# ai-agent-projects

国科大 AI Agent 实践课题简介

随着大模型的到来，智能代理（AI Agent）已经不再是遥不可及的概念，而是我们生活和学习中的一部分。现在，你有机会亲手塑造这个未来！

本次 AI Agent 编程实践课题旨在带领有志于技术和创新的本科生们，通过实践深入了解大模型的奥秘，并亲手打造属于自己的 Agent。

我们将提供Prompt社区（即将发布）的多模态大模型API和Agent开发工作流。

本次实践课题由同学们自由组队，每队可以从以下课题中任选一个，建议不同的团队选择不同的课题：

课题一：互动小说

你是否希望把一部小说变成互动游戏，进入一部小说的世界亲身体验呢？

互动小说，就是用户输入一部小说中的一个章节，AI提取小说中的剧情和角色，自动生成一个互动游戏。

整体流程：
1.	用户输入小说中的一个章节（例如《西游记》中的某一回）。
2.	AI提取小说中的剧情背景和每个角色的特征，这些提取的内容作为后续每次生成的prompt一部分。
3.	AI根据小说内容，把这一章节的剧情拆分成几个关卡，设计每个关卡的剧情内容及其通关条件（都是用一段话来描述），给每个关卡生成一张图片作为背景图片。
4.	游戏开始时，AI生成一张剧情概述的描述图片，作为背景图片。
5.	游戏开始时，列出角色列表，让用户选择角色。
6.	每一关卡开始时，AI把事先拟定的剧情内容和背景图片显示给用户。AI根据整体剧情，选择一个角色（当然不能是用户选中的角色）发言。可以使用平台提供的语音克隆功能，把角色的发言用语音输出。
7.	用户要模拟选中的角色，在规定时间内发言。AI把用户输入的语音转换成文字，判断这个关卡是否通过。
8.	如果关卡通过，则进入下一关卡。
9.	如果关卡未通过，根据聊天记录和整体剧情，AI选择一个角色发言，进入下一轮循环。


课题二：语音狼人杀

狼人杀是一个有趣的 LARP（Live Action Role-Playing）游戏。AI Agent也可以扮演狼人杀中的各种角色，让AI Agent跟人类玩狼人杀游戏。狼人杀考验的是AI的推理能力和隐藏自己真实身份的能力。

要求：
1.	利用平台的实时语音能力，开发一个语音狼人杀游戏，一个真人用户和几个AI角色在同一个房间内语音连线玩狼人杀。
2.	至少需要有法官、狼人、村民、女巫、预言家几个角色，猎人、警察等角色有兴趣的话也可以做。
3.	游戏中有一个角色是真人，其他都是AI Agent。
4.	每个AI Agent和参与游戏的人类都需要遵守游戏规则，角色随机，只能看到该看的信息，不能看到不该看的信息。
5.	Agent需要具备一些基本的游戏技巧（可以通过在 prompt 中指定一些游戏技巧），例如狼人一般不能自爆身份，狼人在大多数情况下不应该自刀，狼人应该学会隐藏自己的身份，女巫和预言家应该善用自己的能力。
6.	Agent需要有分析其他人的发言，推断谁是狼人的能力，不能随机选择。

课题三：情报搜集专家

我们经常需要到网上搜集一些信息，但是很多人并不那么熟练使用搜索引擎。但是现在AI的搜索和总结能力已经很强了。

本课题要求对于一些比较复杂的信息搜集类问题，AI自动分析问题，分步搜索，并阅读搜索结果，得到答案。

Agent的整体流程为：
1.	分析问题，提出搜索词。
2.	调用Google搜索API。
3.	访问搜索到的网页，将网页的主体内容提取出来。
4.	将网页内容发给AI模型，让它回答问题。如果能回答，Agent流程结束。
5.	如果搜索到的内容不足以回答，AI可以选择点击网页中的链接，进入新的网页，重复第3步；也可以选择提出新的搜索词，重复第2步。

要求：对于下面6年Hackergame比赛的32道高难度信息检索类题目，要求AI回答正确至少30%（10道题目）才算课题及格。
-	https://github.com/USTC-Hackergame/hackergame2024-writeups/tree/master/official/%E7%8C%AB%E5%92%AA%E9%97%AE%E7%AD%94%EF%BC%88Hackergame%20%E5%8D%81%E5%91%A8%E5%B9%B4%E7%BA%AA%E5%BF%B5%E7%89%88%EF%BC%89
-	https://github.com/USTC-Hackergame/hackergame2023-writeups/blob/master/official/%E7%8C%AB%E5%92%AA%E5%B0%8F%E6%B5%8B/README.md
-	https://github.com/USTC-Hackergame/hackergame2022-writeups/blob/master/official/%E7%8C%AB%E5%92%AA%E9%97%AE%E7%AD%94%E5%96%B5/README.md
-	https://github.com/USTC-Hackergame/hackergame2021-writeups/blob/master/official/%E7%8C%AB%E5%92%AA%E9%97%AE%E7%AD%94%20Pro%20Max/README.md
-	https://github.com/USTC-Hackergame/hackergame2020-writeups/blob/master/official/%E7%8C%AB%E5%92%AA%E9%97%AE%E7%AD%94++/README.md
-	https://github.com/ustclug/hackergame2018-writeups/blob/master/official/ustcquiz/README.md

要求：AI的能力需要是通用的，不允许把问题硬编码到AI中，不允许搜索题解（这些问题直接去Google搜索能够搜出题解，不能利用搜出来的题解）。

课题四：论文视频讲解

Google有一个爆火的App NotebookLM，它可以输入任意的一篇论文，用AI生成一个两个人对聊的播客，讲解这篇论文。

但是论文仅仅两个人对聊，包含的信息量还是太少，没办法看到论文中的图表，论文中的结构也很难表达清楚。效率更高的论文讲解可能还是类似B站视频的形式。

本课题旨在用AI生成论文的视频讲解，输入任意的一篇论文，生成一个讲解视频。视频的图像部分是一个AI生成的PPT，视频的语音部分是这个PPT的语音讲解。

PPT生成的原理是让大模型根据论文生成若干页的PPT，每一页PPT是一段SVG或者HTML代码。大模型可以在生成PPT内容的同时，生成这页PPT的讲解文字。然后再用语音合成模型把讲解文字合成语音，最后把生成的PPT内容和语音结合，就可以得到讲解视频。

本实验将提供AI生成结构化PPT文字内容的模型和语音合成模型。关于结构化PPT生成，可以体验阿里通义千问app中的PPT生成功能。

加分项：生成的PPT中不只有生成的文字大纲，还有来自论文原文的图表。图表和PPT中的说明文字需要对应。

课题五：多模态AI助手

《Her》是一部2013年的有趣电影，是一个男主角和AI恋爱的故事。OpenAI、Anthropic、Google的最新产品都有《Her》的影子。Her中的Samantha是一个AI操作系统，能听，能看，能说，能操作电脑帮助完成工作，能打电话解决社恐难题，还能给用户提供情绪价值。

当然，满血版的Her我们现在还很难做出来。但我们可以做一个精简版本的，支持语音输入（听）、语音输出（说），支持通过摄像头看到面前的内容（看）。

要求达到Gemini演示视频的能力：https://www.youtube.com/watch?v=UIZAiXYceBI （B站链接：https://www.bilibili.com/video/BV1Xg4y1o7PB/?spm_id_from=333.337.search-card.all.click）
能够根据摄像头看到的内容和用户语音提问的问题，用语音回答问题。

加分项：
1.	支持网络搜索
2.	支持操作手机上的App或者电脑（可以利用AppAgent、Mobile Agent等开源项目）
3.	支持控制智能家居设备

