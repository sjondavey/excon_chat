import pytest
from src.valid_index import ValidIndex, get_excon_manual_index
from src.tree_tools import TreeNode, Tree, split_tree, build_tree_for_regulation
from src.file_tools import process_lines, add_full_reference


class TestTree:
    index_checker = get_excon_manual_index()

    def test_add_to_tree(self):
        tree = Tree("Excon", self.index_checker)
        invalid_reference = 'G.1(C)(xviii)(c)(DD)(9)'
        with pytest.raises(ValueError):
            tree.add_to_tree(invalid_reference, heading_text='')

        #Check all nodes get added
        valid_index = 'G.1(C)(xviii)(c)(dd)(9)'
        tree.add_to_tree(valid_index, heading_text='Some really deep heading here')
        number_of_nodes = sum(1 for _ in tree.root.descendants) # excludes the root node
        assert number_of_nodes == 6

        #check that if a duplicate is added, it does not increase the node count
        sub_index = 'G.1(C)(xviii)'
        tree.add_to_tree(valid_index, heading_text='Some less deep heading here')
        number_of_nodes = sum(1 for _ in tree.root.descendants) # excludes the root node
        assert number_of_nodes == 6



    def test_get_node(self):
        tree = Tree("Excon", self.index_checker)
        invalid_reference = 'G.1(C)(xviii)(c)(DD)(9)'
        with pytest.raises(ValueError):
            tree.get_node(invalid_reference)
        invalid_reference = ''
        with pytest.raises(ValueError):
            tree.get_node(invalid_reference)
        
        assert tree.get_node("Excon") == tree.root
        assert tree.get_node("Excon").full_node_name == ""
        assert tree.get_node("Excon").heading_text == ""

        excon_description = "Exchange control manual hierarchy"
        tree.add_to_tree("Excon", heading_text=excon_description)
        assert tree.get_node("Excon").heading_text == excon_description

        valid_index = 'G.1(C)(xviii)(c)(dd)(9)'
        tree.add_to_tree(valid_index, heading_text='Some really deep heading here')
        assert tree.get_node(valid_index).heading_text == 'Some really deep heading here'
        sub_index = 'G.1(C)(xviii)'
        assert tree.get_node(sub_index).heading_text == ''
        tree.add_to_tree(sub_index, heading_text='Some less deep heading here')
        assert tree.get_node(sub_index).heading_text == 'Some less deep heading here'


def test_split_tree():

    lines = []
    lines.append('A.3 Duties and responsibilities of Authorised Dealers (#Heading) (reference_pdf_document_1.pdf; pg 1)')
    lines.append('some preamble with no reference, but correct spacing here')
    lines.append('    (A) Introduction (#Heading) (reference_pdf_document_1.pdf; pg 2)')
    lines.append('        (i) Authorised Dealers should note that when approving requests in terms of the Authorised Dealer Manual, they are in terms of the Regulations, not allowed to grant permission to clients and must refrain from using wording that approval/permission is granted in correspondence with their clients. Instead reference should be made to the specific section of the Authorised Dealer Manual in terms of which the client is permitted to transact. (reference_pdf_document_2.pdf; pg 1)')
    lines.append('        (ii) In carrying out the important duties entrusted to them, Authorised Dealers should appreciate that uniformity of policy is essential, and that to ensure this it is necessary for the Regulations, Authorised Dealer Manual and circulars to be applied strictly and impartially by all concerned. ')
    lines.append('    (B) Procedures to be followed by Authorised Dealers in administering the Exchange Control Regulations (#Heading)')
    lines.append('        (i) In cases where an Authorised Dealer is uncertain and/or cannot approve the purchase or sale of foreign currency or any other transaction in terms of the authorities set out in the Authorised Dealer Manual, an application should be submitted to the Financial Surveillance Department via the head office of the Authorised Dealer concerned. ')
    lines.append('        (ii) Should an Authorised Dealer have any doubt as to whether or not it may approve an application, such application must likewise be submitted to the Financial Surveillance Department. Authorised Dealers must as a general rule, refrain from their own interpretation of the Authorised Dealer Manual. ')
    lines.append('    (E) Transactions with Common Monetary Area residents (#Heading)')
    lines.append('    Pre-amble to (E)')
    lines.append('        (viii) As an exception to (vi) above, Authorised Dealers may:') 
    lines.append('            (a) sell foreign currency to: ')
    lines.append('                (aa) foreign diplomats, accredited foreign diplomatic staff as well as students with a valid student card from other CMA countries while in South Africa; ')
    lines.append('                (bb) CMA residents in South Africa, to cover unforeseen incidental costs whilst in transit, subject to viewing a passenger ticket confirming a destination outside the CMA;  ')
    lines.append('                (cc) CMA residents in South Africa, to cover unforeseen incidental costs whilst in transit, subject to viewing a passenger ticket confirming a destination outside the CMA;  ')
    lines.append('    Post-amble to E')
    lines.append('some post-amble with no reference, but correct spacing here')

    excon_index = get_excon_manual_index()
    df = process_lines(lines, excon_index)
    add_full_reference(df, excon_index)

    tree = build_tree_for_regulation("split_test", df, excon_index)

    #node_list=[]
    token_limit_per_chunk = 125
    chunked_df = split_tree(tree.root, df, token_limit_per_chunk, excon_index)
    assert len(chunked_df) == 7
    assert chunked_df.iloc[0]['section'] == 'A.3(A)(i)'
    assert chunked_df.iloc[1]['section'] == 'A.3(A)(ii)'
    assert chunked_df.iloc[2]['section'] == 'A.3(B)(i)'
    assert chunked_df.iloc[6]['section'] == 'A.3(E)(viii)(a)(cc)'

