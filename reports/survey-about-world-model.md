# World Models: A Research Survey

## TL;DR
- The paper presents DreamTrue, a multi-view, cross-embodiment robot world model for action-faithful and physically plausible video prediction. [1]
- World models offer a promising alternative to physics-based simulators, yet remain far from practical deployment. [2]
- Vid2World repurposes pre-trained video diffusion models into interactive world models via causalization and action guidance, enhancing action controllability and scalability in complex environments. [3]

## Background
This survey examines world models through published paper abstracts and Hugging Face paper summaries. The selected sources describe distinct research questions within the topic. [1][2]

## Approaches and representations
In *DreamTrue: Action-Faithful Robot World Model with Counterfactual Post-Training*, the paper presents DreamTrue, a multi-view, cross-embodiment robot world model for action-faithful and physically plausible video prediction. [1] *What 30,000 Hours of Ego-centric Video Does Not Teach* places emphasis elsewhere: world models offer a promising alternative to physics-based simulators, yet remain far from practical deployment. [2] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [1][2]

## Training and evidence
In *Vid2World: Crafting Video Diffusion Models to Interactive World Models*, vid2World repurposes pre-trained video diffusion models into interactive world models via causalization and action guidance, enhancing action controllability and scalability in complex environments. [3] *WorldDreamer: Towards General World Models for Video Generation via Predicting Masked Tokens* places emphasis elsewhere: worldDreamer, a world model inspired by large language models, excels at unsupervised visual sequence modeling, generating videos in various scenarios with tasks such as text-to-video conversion and image-to-video synthesis. [4] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [3][4]

## Applications and trade-offs
In *WorldDreamer: Towards General World Models for Video Generation via Predicting Masked Tokens*, worldDreamer, a world model inspired by large language models, excels at unsupervised visual sequence modeling, generating videos in various scenarios with tasks such as text-to-video conversion and image-to-video synthesis. [4] *From Traces to Agentic Worlds: Agentic Language World Models for Interactive Environment Simulation* places emphasis elsewhere: realistic environment replicas are increasingly valuable for training and evaluating LLM agents, yet the original systems may be inaccessible or impractical to reproduce. [5] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [4][5]

## Trends and open problems
The newest papers in this sample broaden the range of methods and tasks under study:
- *DreamTrue: Action-Faithful Robot World Model with Counterfactual Post-Training* (2026-10-08): The paper presents DreamTrue, a multi-view, cross-embodiment robot world model for action-faithful and physically plausible video prediction. [1]
- *What 30,000 Hours of Ego-centric Video Does Not Teach* (2026-10-08): World models offer a promising alternative to physics-based simulators, yet remain far from practical deployment. [2]
- *From Traces to Agentic Worlds: Agentic Language World Models for Interactive Environment Simulation* (2026-10-05): Realistic environment replicas are increasingly valuable for training and evaluating LLM agents, yet the original systems may be inaccessible or impractical to reproduce. [5]

A useful next step is to test these approaches on comparable tasks and to examine where conclusions from one setting transfer to another. The cited abstracts provide distinct cases for that comparison. [1][2][5]

## References
[1] DreamTrue: Action-Faithful Robot World Model with Counterfactual Post-Training. arxiv. https://arxiv.org/abs/2610.12468 (2026-10-08)
[2] What 30,000 Hours of Ego-centric Video Does Not Teach. arxiv. https://arxiv.org/abs/2610.12464 (2026-10-08)
[3] Vid2World: Crafting Video Diffusion Models to Interactive World Models. hf-search. https://huggingface.co/papers/2505.14357 (2025-05-20)
[4] WorldDreamer: Towards General World Models for Video Generation via Predicting Masked Tokens. hf-search. https://huggingface.co/papers/2401.09985 (2024-01-18)
[5] From Traces to Agentic Worlds: Agentic Language World Models for Interactive Environment Simulation. hf-daily. https://huggingface.co/papers/2610.06100 (2026-10-05)
