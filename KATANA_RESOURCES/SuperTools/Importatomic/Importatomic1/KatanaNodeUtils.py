
def getAllChildren(nodes):
    """
    Recursively finds all the children in group nodes or complex nodes such as LiveGroups or Supertools
    :param nodes: list of nodes
    :return: list of all child/grandchild nodes
    """
    return_list = []
    for node in nodes:
        return_list.append(node)
        if hasattr(node, "getChildren"):
            child_nodes = node.getChildren()
            return_list.extend(getAllChildren(child_nodes))
    return return_list