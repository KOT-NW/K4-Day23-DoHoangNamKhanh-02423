# Efficient Inference and Small Language Models: A Research Survey

## TL;DR
- The memory-bound nature of the decoding stage of large language model (LLM) inference incurs significant latency. [1]
- Multimodal large language models have made remarkable progress in bridging vision and language, facilitating various perception tasks essential for human-machine interaction, robotics, and autonomous driving. [2]
- A method reducing key-value cache memory in transformer architectures improves inference throughput without sacrificing performance in language modeling tasks. [3]

## Background
This survey examines efficient inference and small language models through published paper abstracts and Hugging Face paper summaries. The selected sources describe distinct research questions within the topic. [1][2]

## Approaches and representations
In *SparseDecoding: Decoding-Aware Pruning for Accurate and Efficient LLM Inference*, the memory-bound nature of the decoding stage of large language model (LLM) inference incurs significant latency. [1] *DVD: Dynamic Vector Decoding for Efficient MLLM-based Perception* places emphasis elsewhere: multimodal large language models have made remarkable progress in bridging vision and language, facilitating various perception tasks essential for human-machine interaction, robotics, and autonomous driving. [2] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [1][2]

## Training and evidence
In *Layer-Condensed KV Cache for Efficient Inference of Large Language Models*, a method reducing key-value cache memory in transformer architectures improves inference throughput without sacrificing performance in language modeling tasks. [3] *H2O-Danube3 Technical Report* places emphasis elsewhere: h2O-Danube3, a series of small language models, achieves high performance across various benchmarks and is efficient for local inference on smartphones. [4] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [3][4]

## Applications and trade-offs
In *More Than Words: Compositional Tokenization for Efficient Language Models*, language models process and generate text sequentially in token units, and the tokenizer determines how much text each inference step covers. [5] *HARISSA: Inference-Time Self-Checks for Efficient and Safe Local Language Model Deployment* places emphasis elsewhere: running a language model locally offers advantages in privacy, latency, and cost, but local hardware fits only small models, which are less capable than frontier models. [6] The two abstracts describe different targets, so their claims should be compared by setting and evidence rather than treated as one shared score. [5][6]

## Trends and open problems
The newest papers in this sample broaden the range of methods and tasks under study:
- *SparseDecoding: Decoding-Aware Pruning for Accurate and Efficient LLM Inference* (2026-10-08): The memory-bound nature of the decoding stage of large language model (LLM) inference incurs significant latency. [1]
- *DVD: Dynamic Vector Decoding for Efficient MLLM-based Perception* (2026-10-08): Multimodal large language models have made remarkable progress in bridging vision and language, facilitating various perception tasks essential for human-machine interaction, robotics, and autonomous driving. [2]
- *Foundations of Large Language Models* (2026-10-08): This is a book about large language models. [7]

A useful next step is to test these approaches on comparable tasks and to examine where conclusions from one setting transfer to another. The cited abstracts provide distinct cases for that comparison. [1][2][7]

## References
[1] SparseDecoding: Decoding-Aware Pruning for Accurate and Efficient LLM Inference. arxiv. https://arxiv.org/abs/2610.12327 (2026-10-08)
[2] DVD: Dynamic Vector Decoding for Efficient MLLM-based Perception. arxiv. https://arxiv.org/abs/2610.12266 (2026-10-08)
[3] Layer-Condensed KV Cache for Efficient Inference of Large Language Models. hf-search. https://huggingface.co/papers/2405.10637 (2024-05-17)
[4] H2O-Danube3 Technical Report. hf-search. https://huggingface.co/papers/2407.09276 (2024-07-12)
[5] More Than Words: Compositional Tokenization for Efficient Language Models. arxiv. https://arxiv.org/abs/2610.05597 (2026-10-04)
[6] HARISSA: Inference-Time Self-Checks for Efficient and Safe Local Language Model Deployment. arxiv. https://arxiv.org/abs/2609.38006 (2026-09-29)
[7] Foundations of Large Language Models. hf-daily. https://huggingface.co/papers/2501.09223 (2026-10-08)
