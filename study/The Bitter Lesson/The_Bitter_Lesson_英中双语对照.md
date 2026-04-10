# The Bitter Lesson
# 苦涩的教训

*Rich Sutton*
*Rich Sutton（理查德·萨顿）*

March 13, 2019
2019 年 3 月 13 日

---

The biggest lesson that can be read from 70 years of AI research is that general methods that leverage computation are ultimately the most effective, and by a large margin. The ultimate reason for this is Moore's law, or rather its generalization of continued exponentially falling cost per unit of computation. Most AI research has been conducted as if the computation available to the agent were constant (in which case leveraging human knowledge would be one of the only ways to improve performance) but, over a slightly longer time than a typical research project, massively more computation inevitably becomes available. Seeking an improvement that makes a difference in the shorter term, researchers seek to leverage their human knowledge of the domain, but the only thing that matters in the long run is the leveraging of computation. These two need not run counter to each other, but in practice they tend to. Time spent on one is time not spent on the other. There are psychological commitments to investment in one approach or the other. And the human-knowledge approach tends to complicate methods in ways that make them less suited to taking advantage of general methods leveraging computation. There were many examples of AI researchers' belated learning of this bitter lesson, and it is instructive to review some of the most prominent.

从 70 年的 AI 研究中能够得出的最大教训是：那些能够借助算力的通用方法，最终是效果最好的——而且领先幅度很大。其根本原因在于摩尔定律，或者更准确地说，是它的广义形式——单位算力成本持续呈指数下降。大多数 AI 研究进行时都默认"Agent 可获得的算力是常数"（在这种假设下，利用人类知识几乎是提升性能的唯一途径），但只要把时间尺度拉得比一个典型研究项目略长一些，海量增加的算力就必然会到来。为了在较短的时间内做出有意义的改进，研究者倾向于利用自己对该领域的人类知识；但从长远看，真正重要的只有对算力的利用。这两者并不一定冲突，但在实践中往往会相互排斥。花在一边的时间就没法花在另一边。研究者在心理上也会对自己投入的路径形成承诺。而且，基于人类知识的方法往往会让系统变得复杂，从而更难以利用那些依赖算力的通用方法。AI 研究者姗姗来迟地领悟这一苦涩教训的例子有很多，回顾其中最显著的几个很有启发意义。

---

In computer chess, the methods that defeated the world champion, Kasparov, in 1997, were based on massive, deep search. At the time, this was looked upon with dismay by the majority of computer-chess researchers who had pursued methods that leveraged human understanding of the special structure of chess. When a simpler, search-based approach with special hardware and software proved vastly more effective, these human-knowledge-based chess researchers were not good losers. They said that "brute force" search may have won this time, but it was not a general strategy, and anyway it was not how people played chess. These researchers wanted methods based on human input to win and were disappointed when they did not.

在计算机国际象棋领域，1997 年击败世界冠军卡斯帕罗夫的方法是基于大规模、深层次的搜索。在当时，这让大多数一直追求"利用人类对国际象棋特殊结构的理解"的计算机象棋研究者感到沮丧。当一种更简单的、基于搜索的方法——配合专用硬件和软件——被证明效果远远更好时，这些基于人类知识的研究者并不是体面的失败者。他们辩称，"蛮力"搜索也许这一次赢了，但它不是一种通用策略，而且无论如何也不是人类下棋的方式。这些研究者希望依靠人类输入的方法获胜，当事与愿违时，他们感到失望。

---

A similar pattern of research progress was seen in computer Go, only delayed by a further 20 years. Enormous initial efforts went into avoiding search by taking advantage of human knowledge, or of the special features of the game, but all those efforts proved irrelevant, or worse, once search was applied effectively at scale. Also important was the use of learning by self play to learn a value function (as it was in many other games and even in chess, although learning did not play a big role in the 1997 program that first beat a world champion). Learning by self play, and learning in general, is like search in that it enables massive computation to be brought to bear. Search and learning are the two most important classes of techniques for utilizing massive amounts of computation in AI research. In computer Go, as in computer chess, researchers' initial effort was directed towards utilizing human understanding (so that less search was needed) and only much later was much greater success had by embracing search and learning.

在计算机围棋领域也出现了相同的研究进展模式，只是晚了大约 20 年。最初人们投入了大量精力，试图利用人类知识或围棋本身的特殊性质来绕开搜索，但一旦大规模、高效地应用搜索之后，所有这些努力都被证明无关紧要——甚至适得其反。同样重要的是通过自我对弈来学习价值函数（这在许多其他游戏、甚至在国际象棋中也是如此，尽管在 1997 年那个首次击败世界冠军的程序里，学习还没有起到很大作用）。自我对弈学习——以及学习这件事本身——和搜索一样，都能让海量算力得以被调动。搜索和学习是 AI 研究中利用大规模算力最重要的两类技术。在计算机围棋中，和在计算机国际象棋中一样，研究者起初的努力是朝着"利用人类理解（从而减少所需的搜索）"的方向，而真正更大的成功，是后来拥抱搜索和学习之后才获得的。

---

In speech recognition, there was an early competition, sponsored by DARPA, in the 1970s. Entrants included a host of special methods that took advantage of human knowledge—knowledge of words, of phonemes, of the human vocal tract, etc. On the other side were newer methods that were more statistical in nature and did much more computation, based on hidden Markov models (HMMs). Again, the statistical methods won out over the human-knowledge-based methods. This led to a major change in all of natural language processing, gradually over decades, where statistics and computation came to dominate the field. The recent rise of deep learning in speech recognition is the most recent step in this consistent direction. Deep learning methods rely even less on human knowledge, and use even more computation, together with learning on huge training sets, to produce dramatically better speech recognition systems. As in the games, researchers always tried to make systems that worked the way the researchers thought their own minds worked—they tried to put that knowledge in their systems—but it proved ultimately counterproductive, and a colossal waste of researcher's time, when, through Moore's law, massive computation became available and a means was found to put it to good use.

在语音识别领域，20 世纪 70 年代有过一场早期的比赛，由 DARPA 资助。参赛方法中有一大批利用人类知识的特殊方法——关于词的知识、关于音素的知识、关于人类发音器官的知识等等。另一边则是一些更具统计性质、计算量大得多的新方法，基于隐马尔可夫模型（HMM）。结果又一次是：统计方法战胜了基于人类知识的方法。这在之后的几十年里逐步推动了整个自然语言处理领域的重大转变——统计与算力开始主导这个领域。近年来深度学习在语音识别中的崛起，正是这个一以贯之方向上最新的一步。深度学习方法对人类知识的依赖更少，使用的算力更多，再结合在海量训练集上的学习，从而造就了远远更好的语音识别系统。和那些棋类游戏一样，研究者总是试图让系统按照他们认为自己大脑运作的方式去运作——他们试图把这些知识塞进系统里——但当摩尔定律使海量算力变得可用、人们又找到了用好这些算力的方法时，这种做法最终被证明是适得其反的，也是对研究者时间的巨大浪费。

---

In computer vision, there has been a similar pattern. Early methods conceived of vision as searching for edges, or generalized cylinders, or in terms of SIFT features. But today all this is discarded. Modern deep-learning neural networks use only the notions of convolution and certain kinds of invariances, and perform much better.

在计算机视觉领域，也出现了类似的模式。早期的方法把视觉设想为寻找边缘、寻找广义圆柱体，或者用 SIFT 特征来描述。但如今所有这些都已被抛弃。现代深度学习神经网络只使用卷积和某几类不变性的概念，却取得了好得多的效果。

---

This is a big lesson. As a field, we still have not thoroughly learned it, as we are continuing to make the same kind of mistakes. To see this, and to effectively resist it, we have to understand the appeal of these mistakes. We have to learn the bitter lesson that building in how we think we think does not work in the long run. The bitter lesson is based on the historical observations that 1) AI researchers have often tried to build knowledge into their agents, 2) this always helps in the short term, and is personally satisfying to the researcher, but 3) in the long run it plateaus and even inhibits further progress, and 4) breakthrough progress eventually arrives by an opposing approach based on scaling computation by search and learning. The eventual success is tinged with bitterness, and often incompletely digested, because it is success over a favored, human-centric approach.

这是一个很大的教训。作为一个领域，我们还远没有把它真正学到，因为我们仍在犯同类型的错误。要看清这一点并有效地抵制它，我们必须理解这些错误为何如此诱人。我们必须学会这个苦涩的教训：把"我们以为自己是怎么思考的"硬塞进系统里，长远来看是行不通的。这个苦涩教训建立在以下历史观察之上：1) AI 研究者经常试图把知识直接塞进 Agent 里；2) 这在短期内总是有帮助，而且能给研究者带来个人成就感；3) 但从长远看，它会遇到瓶颈，甚至阻碍进一步的进展；4) 真正的突破性进展，最终都是由相反的方法带来的——通过搜索和学习来扩展算力。这种最终的胜利带着苦涩，往往也没能被研究者完全消化，因为它是战胜了一个受偏爱的、以人为中心的方法之后获得的胜利。

---

One thing that should be learned from the bitter lesson is the great power of general purpose methods, of methods that continue to scale with increased computation even as the available computation becomes very great. The two methods that seem to scale arbitrarily in this way are *search* and *learning*.

从这个苦涩教训中应当领悟的一件事是：通用方法拥有巨大的力量——那些能够随着算力增加而持续扩展的方法，哪怕在可用算力已经变得非常巨大时仍然如此。以这种方式看起来能够任意扩展的两种方法，是*搜索*和*学习*。

---

The second general point to be learned from the bitter lesson is that the actual contents of minds are tremendously, irredeemably complex; we should stop trying to find simple ways to think about the contents of minds, such as simple ways to think about space, objects, multiple agents, or symmetries. All these are part of the arbitrary, intrinsically-complex, outside world. They are not what should be built in, as their complexity is endless; instead we should build in only the meta-methods that can find and capture this arbitrary complexity. Essential to these methods is that they can find good approximations, but the search for them should be by our methods, not by us. We want AI agents that can discover like we can, not which contain what we have discovered. Building in our discoveries only makes it harder to see how the discovering process can be done.

从这个苦涩教训中应当领悟的第二个普遍观点是：心智的实际内容是极其复杂、无可救药地复杂的；我们应当停止试图用简单的方式去思考心智的内容，比如用简单的方式去思考空间、物体、多 Agent 或对称性。这些东西都是那个任意的、本质上就很复杂的外部世界的一部分。它们不应该是被"内建"进系统里的东西，因为它们的复杂度是无穷的；相反，我们应该内建的只是那些能够发现并捕捉这种任意复杂性的元方法（meta-methods）。这些方法的关键在于它们能够找到好的近似，但对这些近似的搜索应该由我们的方法去完成，而不是由我们自己去完成。我们想要的是能够像我们一样去"发现"的 AI Agent，而不是装着我们已经发现的东西的 AI Agent。把我们的发现硬塞进系统里，只会让"如何完成发现这个过程本身"变得更难看清。
