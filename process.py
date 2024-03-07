#! /usr/bin/python3
from typing import List, Tuple, TextIO
from enum import Enum
import re
import sys
import os


class Iterator:
    
    def __init__(self, list):
        self.list = list
        self.idx = 0

    def end(self):
        return self.idx >= len(self.list)
    
    def next_value(self) -> str:
        self.idx += 1
        return self.value()

    def value(self) ->str:
        return self.list[self.idx] if not self.end() else None


clear_line_pattern = re.compile('^I\\d{8} \\d{2}:\\d{2}:\\d{2}[.]\\d+ \\d+ concurrent_btree.h:\\d+\\] ')
kv_pattern = re.compile('\\[([^=]+)=([^=]+)\\]')


class Node:
    class NodeType(Enum):
        INTERNAL = 1
        LEAF = 2

    childs = None
    separators = None
    node_type: NodeType = None
    pointer: int = None
    version: int = None
    name: str = None

    next_id = 0
    id_map = {}
    @staticmethod
    def next_name(pointer: int):
        if pointer not in Node.id_map:
            Node.id_map[pointer] = f'N{Node.next_id}'
            Node.next_id += 1
        return Node.id_map[pointer]

    def __init__(self, iter: Iterator):
        self.childs = []
        v = iter.value().lower()
        my_depth = len(v) - len(v.lstrip(' '))
        v = v.strip()
        if v.startswith('internal'):
            self.node_type = Node.NodeType.INTERNAL
            v = v[len('internal '):]            
            self.separators = []
        elif v.startswith('leaf'):
            self.node_type = Node.NodeType.LEAF
            v = v[len('leaf '):]            
        else:
            raise RuntimeError("Invalid node type: " + v)
        
        fields=v.split(" ")
        self.pointer = int(fields[0][:-1],0)
        self.name = self.next_name(self.pointer)
        fields=fields[1:]
        if self.node_type == Node.NodeType.LEAF:
            for f in fields:
                m = kv_pattern.search(f)
                assert(m)
                self.childs.append((m.group(1), m.group(2)))
            iter.next_value()
            return
        assert(not fields) # must be empty

        iter.next_value()
        while True:
            v = iter.value()
            if not v:
                return
            v = v.lower()
            depth = len(v) - len(v.lstrip(' ')) 
            v = v.strip()
            if depth <= my_depth:
                return
            if v.startswith('key'):
                self.separators.append(v.split()[1])
                iter.next_value()
            else:
                self.childs.append(Node(iter))                                            

    def print(self, file: TextIO):
        if self.node_type == Node.NodeType.INTERNAL:
            label = f"|{'|'.join(self.separators)}|"
            file.write(f'{self.name}[label="{self.name} {label}"]')
            for c in self.childs:
                file.write(f"{self.name} -> {c.name};\n")
                c.print(file)
        else:
            for k, v in self.childs:
                file.write(f"{self.name} -> {'K' + k};\n")
        
    
class CBTree:
    root: Node

    def print(self, file: TextIO):
        file.write("digraph G {\n")
        self.root.print(file)
        file.write("}\n")

def clear_line(line):
    m = clear_line_pattern.match(line)
    if m:
        return line[m.span()[1]:]
    return line


def parse_tree(lines: List[str]) -> CBTree:
    lines_purged = list(map(clear_line, lines))
    #print("\n".join(lines_purged))
    res = CBTree()
    res.root = Node(Iterator(lines_purged))
    return res

def load_test_inserts(file: str) -> List[Tuple[int, CBTree]]:
    res = []
    with open(file) as inp:
        lines = inp.readlines()
    graph = []
    insert_key = None
    for x in lines:
        if x.startswith("WARNING: Logging before InitGoogleLogging() is written to STDERR"):
            continue
        if x.startswith("INSERT"):
            if insert_key is not None:
                res.append((insert_key, parse_tree(graph) ))
            
            insert_key = int(x.split()[1])
            graph = []
            continue
        if x.startswith("Failed on key:"):
            insert_key = x[len("Failed on key:"):].strip()
            continue
        if "concurrent_btree" in x:
            graph.append(x)
            continue
        if x.strip:
            raise RuntimeError("Invalide line: " + x) 
        
    if insert_key:
        res.append((insert_key, parse_tree(graph) ))

    return res

def generate_example():
    my_list = load_test_inserts(sys.argv[1])
    idx = 0
    for k,v in my_list: 
        print("Processing:", idx)
        k = f'{k:03}'
        k = str(k)[1:] + str(k)[0]

        fname = f"{idx:03}_ins_key{k}"
        fpath = os.path.join("/Users/zmartonka/graphs", fname +'.gv')
        ifpath = os.path.join("/Users/zmartonka/graphs", fname + '.pdf')
        with open(fpath, "wt") as out:
            v.print(out)
        idx += 1
        os.system(f"dot -Tpdf {fpath} -o {ifpath}")

def generate_real_error():
    fail_key, g = load_test_inserts("logs/wrong_tree_key_38")[0]
    fname = f"fail_{fail_key}"
    fpath = os.path.join("/Users/zmartonka/graphs", fname +'.gv')
    ifpath = os.path.join("/Users/zmartonka/graphs", fname + '.pdf')
    with open(fpath, "wt") as out:
        g.print(out)
    os.system(f"dot -Tpdf {fpath} -o {ifpath}")

if __name__ == "__main__":
    #generate_example()
    generate_real_error()