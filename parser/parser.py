import nltk
import sys



TERMINALS = """
Adj -> "country" | "dreadful" | "enigmatical" | "little" | "moist" | "red"
Adv -> "down" | "here" | "never"
Conj -> "and" | "until"
Det -> "a" | "an" | "his" | "my" | "the"
N -> "armchair" | "companion" | "day" | "door" | "hand" | "he" | "himself"
N -> "holmes" | "home" | "i" | "mess" | "paint" | "palm" | "pipe" | "she"
N -> "smile" | "thursday" | "walk" | "we" | "word"
P -> "at" | "before" | "in" | "of" | "on" | "to"
V -> "arrived" | "came" | "chuckled" | "had" | "lit" | "said" | "sat"
V -> "smiled" | "tell" | "were"
"""

NONTERMINALS = """
S -> NP VP|NP VP Conj VP| S Conj S

NP -> N|N NP| Det NP| Adj NP | NP P NP

VP -> V | V VP| VP NP |VP P NP| VP Conj NP | VP Adv| Adv VP |VP Adv VP 



"""

grammar = nltk.CFG.fromstring(NONTERMINALS + TERMINALS)
parser = nltk.ChartParser(grammar)
f=None

def main():

    # If filename specified, read sentence from file
    if len(sys.argv) == 2:
        with open(sys.argv[1]) as f:
            s = f.read()

    # Otherwise, get sentence as input
    else:
        s = input("Sentence: ")

    # Convert input into list of words
    s = preprocess(s)

    # Attempt to parse sentence
    try:
        trees = list(parser.parse(s))
    except ValueError as e:
        print(e)
        return
    if not trees:
        print("Could not parse sentence.")
        return

    # Print each tree with noun phrase chunks
    for tree in trees:
        tree.pretty_print()

        print("Noun Phrase Chunks")
        for np in np_chunk(tree):
            print(" ".join(np.flatten()))


def preprocess(sentence):
    """
    Convert `sentence` to a list of its words.
    Pre-process sentence by converting all characters to lowercase
    and removing any word that does not contain at least one alphabetic
    character.
    """
    tokens=nltk.word_tokenize(sentence)
    word_list=[]
    for token in tokens:
        for letter in token:
            if letter.isalpha():    
                word_list.append(token.lower())
                break
    return word_list
    


def np_chunk(tree):
    global f
    f=tree
    """
    Return a list of all noun phrase chunks in the sentence tree.
    A noun phrase chunk is defined as any subtree of the sentence
    whose label is "NP" that does not itself contain any other
    noun phrases as subtrees.
    """
    result=[]
    for subtree in tree.subtrees():
        if subtree.label()=='N' and not(list(subtree.subtrees(lambda x:x.label()=='NP' and x!=subtree))):
            result.append(subtree)
    return result
    
    
    



if __name__ == "__main__":
    main()
'''
Holmes sat.
I had a little moist red paint in the palm of my hand.
Holmes lit a pipe.
We arrived the day before Thursday.
Holmes sat in the red armchair and he chuckled.
My companion smiled an enigmatical smile. 
Holmes chuckled to himself.
She never said a word until we were at the door here.
Holmes sat down and lit his pipe.
I had a country walk on Thursday and came home in a dreadful mess.
'''