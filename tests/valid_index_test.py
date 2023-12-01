import pytest
from src.valid_index import ValidIndex, get_excon_manual_index

class TestValidIndex:
    index_checker = get_excon_manual_index()

    def test_is_valid_reference(self):
        blank_reference = ""
        assert not self.index_checker.is_valid_reference(blank_reference)

        long_reference = 'G.1(C)(xviii)(c)(dd)(9)'
        assert self.index_checker.is_valid_reference(long_reference)
        short_reference = 'G.1(C)'        
        assert self.index_checker.is_valid_reference(short_reference)

        reference_on_exclusion_list = 'Legal context'
        assert self.index_checker.is_valid_reference(reference_on_exclusion_list)

        invalid_reference = 'G.1(C)(xviii)(c)(c)(9)'
        assert not self.index_checker.is_valid_reference(invalid_reference)
        invalid_reference = 'G.1(C)(xviii)(c)(DD)(9)'
        assert not self.index_checker.is_valid_reference(invalid_reference)
        invalid_reference = 'G.1(C)(xviii)(c)(9)(dd)'
        assert not self.index_checker.is_valid_reference(invalid_reference)
        invalid_reference = 'G.1(xviii)'
        assert not self.index_checker.is_valid_reference(invalid_reference)

    def test_extract_valid_reference(self):
        assert self.index_checker.extract_valid_reference('B.18 Gold (B)(i)(b)') == 'B.18(B)(i)(b)'
        assert self.index_checker.extract_valid_reference('   B.18 Gold (B)(i)(b)') == 'B.18(B)(i)(b)'
        #assert self.index_checker.extract_valid_reference('B.18 Gold (B)(i)(ii)')  is None
        assert self.index_checker.extract_valid_reference('B.18 Gold (B)(i)(ii)')  == 'B.18(B)(i)'
        assert self.index_checker.extract_valid_reference('A.1') == 'A.1'
        assert self.index_checker.extract_valid_reference('B.18 Gold (B)(i)(b) hello') == 'B.18(B)(i)(b)' # text at the end
        #assert self.index_checker.extract_valid_reference('B.18 Gold (B)(i)(b) (hello)') == None  # the text at the end contains an "("
        assert self.index_checker.extract_valid_reference('B.18 Gold (B)(i)(b) (hello)') == 'B.18(B)(i)(b)'

    def test_split_reference(self):
        long_reference = 'G.1(C)(xviii)(c)(dd)(9)'
        components = self.index_checker.split_reference(long_reference)
        assert len(components) == 6
        assert components[0] == 'G.1'
        assert components[1] == '(C)'
        assert components[2] == '(xviii)'
        assert components[3] == '(c)'
        assert components[4] == '(dd)'
        assert components[5] == '(9)'

        short_reference = 'G.1(C)'        
        components = self.index_checker.split_reference(short_reference)
        assert len(components) == 2
        assert components[0] == 'G.1'
        assert components[1] == '(C)'


        invalid_reference = 'G.1(C)(xviii)(c)(DD)(9)'
        with pytest.raises(ValueError):
            components = self.index_checker.split_reference(invalid_reference)

        invalid_reference = 'G.1(C)(xviii)(c)(d)(9)'
        with pytest.raises(ValueError):
            components = self.index_checker.split_reference(invalid_reference)

        reference_on_exclusion_list = 'Legal context'
        components = self.index_checker.split_reference(reference_on_exclusion_list)
        assert components[0] == reference_on_exclusion_list

    def test_get_parent_reference(self):
        reference = 'G.1(C)(xviii)(c)(dd)(9)'
        assert self.index_checker.get_parent_reference(reference) == 'G.1(C)(xviii)(c)(dd)'
        with pytest.raises(ValueError):
            components = self.index_checker.get_parent_reference("")


    def test_parse_line_of_text(self):
        string_with_incorrect_indent = "               (aa) the name and registration number of the applicant company; "
        with pytest.raises(ValueError):
            indent, index, remaining_text = self.index_checker.parse_line_of_text(string_with_incorrect_indent)

        string_with_mismatched_indent_and_index = "                (c) the name and registration number of the applicant company; "
        with pytest.raises(ValueError):
            indent, index, remaining_text = self.index_checker.parse_line_of_text(string_with_mismatched_indent_and_index)

        string_with_correct_indent = "                (aa) the name and registration number of the applicant company; "
        indent, index, remaining_text = self.index_checker.parse_line_of_text(string_with_correct_indent)
        assert indent == 4
        assert index == '(aa)'
        assert remaining_text == 'the name and registration number of the applicant company; '
        
        reference_on_exclusion_list = 'Legal context'
        indent, index, remaining_text = self.index_checker.parse_line_of_text(reference_on_exclusion_list)
        assert indent == 0
        assert index == 'Legal context'
        assert remaining_text == ''

        reference_on_exclusion_list_wrong_indent = '    Legal context'
        with pytest.raises(ValueError):
            indent, index, remaining_text = self.index_checker.parse_line_of_text(reference_on_exclusion_list_wrong_indent)

        

    def test___extract_reference_from_string(self):
        string_with_no_reference = 'Africa means any country forming part of the African Union.'
        index, string = self.index_checker._extract_reference_from_string(string_with_no_reference)
        assert index == ""
        assert string == string_with_no_reference

        # tests for each of the numbering patters used in excon_index_patterns
        string_with_reference = 'A.1 Definitions'
        index, string = self.index_checker._extract_reference_from_string(string_with_reference)
        assert index == "A.1"
        assert string == 'Definitions'

        string_with_reference = '(A) Authorised Dealers'
        index, string = self.index_checker._extract_reference_from_string(string_with_reference)
        assert index == "(A)"
        assert string == 'Authorised Dealers'

        string_with_reference = '(xxiii) Authorised Dealers must reset their application numbering systems to zero at the beginning of each calendar year.'
        index, string = self.index_checker._extract_reference_from_string(string_with_reference)
        assert index == "(xxiii)"
        assert string == 'Authorised Dealers must reset their application numbering systems to zero at the beginning of each calendar year.'

        string_with_reference = '(a) a list of application numbers generated but not submitted to the Financial Surveillance Department;'
        index, string = self.index_checker._extract_reference_from_string(string_with_reference)
        assert index == "(a)"
        assert string == 'a list of application numbers generated but not submitted to the Financial Surveillance Department;'

        string_with_reference = '(dd) CMA residents who travel overland to and from other CMA countries through a SADC country up to an amount not exceeding R25 000 per calendar year. This allocation does not form part of the permissible travel allowance for residents; and'
        index, string = self.index_checker._extract_reference_from_string(string_with_reference)
        assert index == "(dd)"
        assert string == 'CMA residents who travel overland to and from other CMA countries through a SADC country up to an amount not exceeding R25 000 per calendar year. This allocation does not form part of the permissible travel allowance for residents; and'

        string_with_reference = '(1) the full names and identity number of the applicant;'
        index, string = self.index_checker._extract_reference_from_string(string_with_reference)
        assert index == "(1)"
        assert string == 'the full names and identity number of the applicant;'

        heading_on_exclusion_list = 'Legal context'
        index, string = self.index_checker._extract_reference_from_string(heading_on_exclusion_list)
        assert index == heading_on_exclusion_list
        assert string == ""
