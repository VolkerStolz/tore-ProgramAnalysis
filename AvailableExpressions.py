from typing import List, Union, Callable
from syntax import *
from examples import *

class Node:
    def __init__(self):
        self.label = None   # Label for this node in the control flow graph
        self.stmt = None    # Statement represented by this node
        self.expression = None # Expression represented by this node
        self.gen = set()    # Expressions generated in this node
        self.kill = set()   # Expressions killed in this node
        self.entry = set()  # Assignments live at entry to this node
        self.exit = set()   # Assignments live at exit from this node
        self.while_loop_number = None # Number of the while loop this node belongs to
        self.first_node_in_while = False # True if this node is the first node in a while loop
        self.last_node_in_while = False # True if this node is the last node in a while loop
        #self.predecessors: list(Node) = [] # Predecessor nodes in the control flow graph
        #self.successors: list(Node) = [] # Successor nodes in the control flow graph
        self.coming_in: list(Node) = [] # List of nodes coming in from in the control flow graph
        self.going_out: list(Node) = [] # List of nodes going out to in the control flow graph
        self.entry_state = set()  # Analysis state at entry to this node (used for chaotic iteration)
        self.exit_state = set()  # Analysis state at exit from this node (used for chaotic iteration)

    def __iter__(self):
        current = self.head
        while current is not None:
            yield current
            current = current.next

    def add_predecessor(self, pred_node):
        """Add a predecessor node and automatically update the coming_in list."""
        if pred_node not in self.coming_in:
            self.coming_in.append(pred_node)
            pred_node.going_out.append(self)
            self.coming_in.append(pred_node)

    # this function not needed? (logic already in above function)
    def add_successor(self, succ_node):
        """Add a successor node and automatically update the going_out list."""
        if succ_node not in self.going_out:
            self.going_out.append(succ_node)
            succ_node.coming_in.append(self)
            self.going_out.append(succ_node)

    def __repr__(self):
        return f"Node(label={self.label})"

    '''
    def __repr__(self):
        return f"Node(entry={self.entry}, exit={self.exit})"
    '''



class AvailableExpressionsAnalysis:

    def __init__(self) -> None:
        self.FV: list[(Assignment, int)] = [] #list of assignments with corresponding label, stored as Assignment for parsing Variable and Expression
        self.label = 0
        self.cfg: list[(int, int)] = []
        self.nodes: list[Node] = []
        self.previous_node_label = 0
        self.if_then_else = False
        self.while_loop = False
        self.is_first_node_in_while = False
        self.is_last_node_in_while = False
        self.first_node_in_while: list[Node] = []
        self.first_node = None
        self.was_last_node_in_while = False
        self.last_node_in_while: list[Node] = []
        self.node = None
        self.last_node = None
        self.current_node = None
        self.previous_node = None
        self.expr_node = False
        #self.node_created = False

    # Create the CFG as well as the nodes containing necessary information for doing an analysis (can later move to superclass)
    def create_cfg(self, program: Statement) -> list((int, int)):
        assert isinstance(program, CompoundStatement)
        for stmt in program.statements:
            self.create_cfg_statement(stmt)
        return self.cfg
    
    # Dealing with expressions
    def create_cfg_expression(self, expr):
        if isinstance(expr, Variable):
            assert isinstance(expr.name, str)
        elif isinstance(expr, Constant):
            assert isinstance(expr.value, int)
        elif isinstance(expr, BinaryOperation):
            # Create a node for the expression
            if (self.is_first_node_in_while or self.if_then_else):
                self.node = Node()
                self.label = self.label + 1
                self.node.label = self.label
                self.node.expression = expr
                self.nodes.append(self.node)
                print("Binary operation Node created: ", self.node.label, "\n")
                # Add to control flow graph
                self.cfg.append((self.previous_node_label, self.node.label))

                if (self.is_first_node_in_while):
                    # Add the first node in the while loop to the stack
                    self.first_node_in_while.append(self.node)
                    #self.is_first_node_in_while = True
            self.previous_node_label = self.node.label
            self.previous_node = self.node

    # Dealing with statements (using function above as helper function for expressions)
    def create_cfg_statement(self, stmt):
        if isinstance(stmt, Assignment):
            self.node = Node()
            self.label = self.label + 1
            self.node.label = self.label
            self.node.stmt = stmt
            self.current_node = self.node
            self.nodes.append(self.node)
            print("Stmt Node created: ", self.node.label, "\n")
            #self.node_created = True

            if (self.is_last_node_in_while):
                self.last_node_in_while.append(self.node)
                self.is_last_node_in_while = True

            self.create_cfg_expression(stmt.variable)
            self.create_cfg_expression(stmt.expression)
        elif isinstance(stmt, WhileLoop):
            self.while_loop = True
            self.create_cfg_expression(stmt.condition)
            for s in stmt.body:
                if (s == stmt.body.statements[0]):
                    self.is_first_node_in_while = True
                if (s == stmt.body.statements[-1]):
                    self.is_last_node_in_while = True
                self.create_cfg_statement(s)
            while_loop = False
            was_last_node_in_while = True
        elif isinstance(stmt, IfThenElse):
            self.if_then_else = True
            self.create_cfg_expression(stmt.condition)
            self.if_then_else = False
            for s in stmt.true_branch:
                self.create_cfg_statement(s)
            for s in stmt.false_branch:
                self.create_cfg_statement(s)
            
        elif isinstance(stmt, CompoundStatement):
            for s in stmt.statements:
                self.create_cfg_statement(s)

        # Logic for dealing with While loops:
                
        if (self.is_first_node_in_while):
            self.first_node_in_while.append(self.node)
            self.is_first_node_in_while = False
        elif (self.is_last_node_in_while):
            self.last_node_in_while.append(self.node)
            self.is_last_node_in_while = False
        elif (self.was_last_node_in_while):
            # Pop from stack to support nested while loops
            self.first_in_while = self.first_node_in_while.pop()
            self.last_in_while = self.last_node_in_while.pop()
            # CGF of the while loop
            self.cfg.append((self.first_in_while.label, self.node.label))
            # add_predecessor updates the coming in and going out lists
            #node.add_predecessor(self.first_in_while)
            self.first_in_while.add_successor(self.node)
            #line below is not needed?
            #self.first_in_while.going_out.append(node)
            self.cfg.append((self.last_in_while.label, self.node.label))
            #node.add_predecessor(self.last_in_while)
            self.last_in_while.add_successor(self.node)
            #line below is not needed?
            #self.last_in_while.going_out.append(node)
            self.was_last_node_in_while = False

        # Logic for dealing with other nodes:
            
        elif (self.previous_node is not None):
            self.cfg.append((self.previous_node_label, self.node.label))
            #node.add_predecessor(self.previous_node)
            self.previous_node.add_successor(self.node)
            #line below is not needed?
            #self.previous_node.going_out.append(node)
        # In any case, the current node becomes the previous node for the next iteration
        self.previous_node_label = self.node.label
        self.previous_node = self.node
        

    #this function is not needed currently
    def create_cfg_while(self, stmt):
        for i in range(0, len(stmt.body)):
            if (i == 0):
                self.create_cfg_expression(stmt.condition)
            elif (i == len(stmt.body) - 1):
                self.create_cfg_expression(stmt.body[i])
                self.create_cfg_statement(stmt.body[i])
                
    def analyze(self, nodes: list): #nodes: list of nodes, cfg: control flow graph
        for node in nodes:
            if node.expression is not None:
                if node.expression in self.FV:
                    node.gen = node.expression

            elif node.stmt is not None:
                if node.stmt not in self.FV:
                    self.FV.append((node.stmt, node.label))
                    node.gen = node.stmt
                else:
                    node.kill = node.stmt
                
    def print_nodes(self, nodes : list, cfg : list):
        print("Control Flow Graph: ")
        print(cfg)

        for node in nodes:
            print(f"Node {node.label}: Predecessors={node.coming_in} Successors={node.going_out} gen={node.gen}, kill={node.kill}, entry={node.entry}, exit={node.exit}")
        
                
        
        






def main():
    #Available expressions analysis:
    analysis = AvailableExpressionsAnalysis()

    # Create the CFG, with nodes containing necessary information for doing an analysis
    cfg = analysis.create_cfg(book_example)
    
    # Analyze the program
    nodes = analysis.nodes
    analysis.analyze(nodes)

    # Print the results
    analysis.print_nodes(nodes, cfg)

if __name__ == "__main__":
    main()