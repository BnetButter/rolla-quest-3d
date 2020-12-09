#!/bin/bash
# Clears the screen
tput reset
BLACK=$(tput setaf 0)
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
BLUE=$(tput setaf 4)
MAGENTA=$(tput setaf 5)
CYAN=$(tput setaf 6)
WHITE=$(tput setaf 7)
ORANGE=$(tput setaf 202)
RESET=$(tput sgr0)

section() {
    echo -e "\n$BLUE===========================================================================================================================$RESET"
}

subsection() {
    echo -e "\n$YELLOW---------------------------------------------------------------------------------------------------------------------------$RESET"
}

echo Welcome to grade.sh! Your code is being graded below:
section
echo -e "Optionally, run this script as follows to silence debugging:\n    $ $MAGENTA ./grade.sh onlydothisaftercompletingthebasics$RESET"
section
echo "See the below if you see warnings about any of the following packages not installed:"
echo -e "    $  $MAGENTA""pip3 install --upgrade python-Levenshtein mypy pudb monkeytype py2cfg black --user$RESET"
echo -e "    $  $MAGENTA""sudo dnf/apt/zypper install -y install python3-black python3-mypy cppcheck clang-format cmake make ShellCheck$RESET"
echo -e "    shfmt can be installed by binary -- see the .gitlab-ci.yml"

check_hashes() {
    # This should be run before any file students could potentially edit.
    # Assumes you've addded the relevant files to hash_gen.sh
    # usage: check_hashes
    # () creates a subshell, and so no need to cd back
    (
        cd .admin_files
        bash hash_gen.sh
        # cd ..
    )
    if diff .admin_files/hashes.txt .admin_files/grader_hashes.txt &>/dev/null; then
        :
        # echo "Hashes ok"
    else
        section
        echo -e "$RED\nDon't edit any of the auotgrader's files, or you will fail!$RESET"
        echo "Notice the files listed below, with the long hashes in front of them."
        echo -e "Those are the files you broke.\n"
        diff .admin_files/hashes.txt .admin_files/grader_hashes.txt
        echo -e "\nIf you are seeing this, then type:"
        echo "    $ $MAGENTA git log$RESET"
        echo "Then look at the log to find the first four letters of the hash of the instructor's last commit; copy it."
        echo "Then type:"
        echo "    $ $MAGENTA git checkout firstfourlettersofthehashoftheinstructorslastcommit fileorfolderyoubroke $RESET"
        echo -e "You must do this for each file you broke (or just the super-folder of the grader-files), and then re-run grade.sh.\n"
        grade=0
        echo "You edited our stuff, and so you get 0; see the output for details" >>"$student_file"
        echo $grade >>"$student_file"
        exit 1
    fi
}

grade_update() {
    # Updates grade and prints, based on the return code of preceeding statement
    # Expects grade for each unit/test to be 0-100
    # Usage: grade_update test_name points_to_add expected_retcode
    return_status=$?
    check_hashes
    echo Test for: "$1" >>"$student_file"
    if [ "$return_status" == "$3" ]; then
        if [ "$2" -lt 100 ]; then
            echo "$RED    gives you $2 more points$RESET" >>"$student_file"
        else
            echo "$GREEN    gives you $2 more points$RESET" >>"$student_file"
        fi
        ((grade = grade + "$2"))
    else
        echo "$RED    gives you 0 more points$RESET" >>"$student_file"
    fi
    ((num_tests = num_tests + 1))
    echo >>"$student_file"
}

unit_tests() {
    section
    echo "Running unit tests, if any:"
    # Executes a directory of our python unit tests.
    # Assumes they don't neeed any standard input (write a custom line for that).
    # Usage: unit_tests
    if [ "$language" = "cpp" ]; then
        glob_expr="unit_tests/*.cpp"
        pushd .admin_files >/dev/null 2>&1
        mkdir -p build >/dev/null 2>&1
        pushd build >/dev/null 2>&1
        cmake .. -DCMAKE_BUILD_TYPE=Debug -DMAIN_FILE:STRING="$main_file" >/dev/null 2>&1
        make >/dev/null 2>&1
        popd >/dev/null 2>&1
        popd >/dev/null 2>&1
        check_hashes
    elif [ "$language" = "python" ]; then
        glob_expr="unit_tests/*.py"
    elif [ "$language" = "bash" ]; then
        glob_expr="unit_tests/*.sh"
    fi

    for testpath in $glob_expr; do
        subsection
        expected_retcode=$(((RANDOM % 250) + 5))
        filename=$(basename "$testpath")
        if [ "$language" = "cpp" ]; then
            testname="$(basename "$filename" .cpp)"
            echo Running: $ " $MAGENTA"timeout 15 ./.admin_files/build/"$testname" "$expected_retcode""$RESET"
            timeout 15 ./.admin_files/build/"$testname" "$expected_retcode"
        elif [ "$language" = "python" ]; then
            echo Running: $ " $MAGENTA"timeout 15 python3 unit_tests/"$filename" "$expected_retcode""$RESET"
            timeout 15 python3 unit_tests/"$filename" "$expected_retcode"
        elif [ "$language" = "bash" ]; then
            echo Running: $ " $MAGENTA"timeout 15 bash unit_tests/"$filename" "$expected_retcode""$RESET"
            timeout 15 bash unit_tests/"$filename" "$expected_retcode"
        fi
        if [ $? -eq "$expected_retcode" ]; then
            grade_update "$filename" 100 0
        else
            grade_update "$filename" 0 0
            # https://stackoverflow.com/questions/20010199/how-to-determine-if-a-process-runs-inside-lxc-docker#20012536
            if [ "$annoying_nodebug" = "onlydothisaftercompletingthebasics" ] || grep 'docker\|lxc' /proc/1/cgroup >/dev/null 2>&1; then
                echo Run this script locally with debugging details.
            else
                if [ "$language" = "cpp" ]; then
                    debug_cmd=(gdb '--eval-command="break main"' '--eval-command="run"' --args ./.admin_files/build/"$testname" 123)
                elif [ "$language" = "python" ]; then
                    debug_cmd=("$pudb3" "$testpath" 123)
                elif [ "$language" = "bash" ]; then
                    debug_cmd=(bash -x "$testpath" 123)
                    # TODO a real bash debugger like bashdb?
                fi
                echo -e "\nHit enter to debug this failing test as follows:\n\t$ $MAGENTA" "${debug_cmd[@]}"
                read -r
                "${debug_cmd[@]}"
            fi
        fi
        check_hashes
    done
}

stdio_tests() {
    section
    echo "Running Standard Input/Output (std io) tests, if any:"
    # Tests a python script (first and only arg) against directory of std-in/out
    # Saves outputs and diffs
    # Usage: stdio_tests main_file.py

    # For C++, build the student's main()
    if [ "$language" = "cpp" ]; then
        prog_name=("./program" "$main_file_arguments")
        # g++ -Wall -Werror -Wpedantic -g -std=c++14 $1 -o "$prog_name"
        # TODO: Can this be any more discerning, in case of multiple main()s?
        g++ -Wall -Werror -Wpedantic -g -std=c++14 ./*.cpp -o "${prog_name[0]}"
    elif [ "$language" = "python" ]; then
        prog_name=(python3 "$1" "$main_file_arguments")
    elif [ "$language" = "bash" ]; then
        prog_name=(bash "$1" "$main_file_arguments")
    fi

    rm -rf stdio_tests/outputs/*
    for testpath in stdio_tests/inputs/*.txt; do
        filename=$(basename "$testpath")
        testname="${filename%_*}"
        subsection
        echo -e "We're running: $ $MAGENTA" "${prog_name[@]}" "<$testpath" ">stdio_tests/outputs/$testname"_output.txt"$RESET"
        t0=$(date +%s.%N)
        timeout 20 "${prog_name[@]}" <"$testpath" >stdio_tests/outputs/"$testname"_output.txt
        check_hashes
        echo -e "Your program took the following number of seconds to run the main driver on a sample input:"
        echo -e "print($(date +%s.%N) - $t0)" | python3
        diff -y -W 200 stdio_tests/goals/"$testname"_output.txt stdio_tests/outputs/"$testname"_output.txt >stdio_tests/diffs/"$testname".txt
        vimdiff stdio_tests/goals/"$testname"_output.txt stdio_tests/outputs/"$testname"_output.txt -c TOhtml -c "w! stdio_tests/diffs/$testname.html" -c 'qa!' >/dev/null 2>&1
        if [ "$fuzzy_partial_credit" = false ]; then
            echo Diffs are computed rigidly -- no partial credit!
            diff stdio_tests/goals/"$testname"_output.txt stdio_tests/outputs/"$testname"_output.txt >/dev/null 2>&1
            grade_update "$testpath" 100 0
            # Just a useless placeholder here:
            fuzzy_diff=0
        else
            echo Diffs are computed fuzzy -- with partial credit!
            fuzzy_diff=$(python3 .admin_files/fuzzydiffer.py "stdio_tests/goals/$testname"_output.txt stdio_tests/outputs/"$testname"_output.txt)
            grade_update "$testpath" "$fuzzy_diff" 0
        fi
        diff stdio_tests/goals/"$testname"_output.txt stdio_tests/outputs/"$testname"_output.txt >/dev/null 2>&1
        if [ "$?" -eq 0 ] || [ "$fuzzy_diff" -eq 100 ]; then
            # bash's no-op is most clear positive logic here...
            :
        else
            if [ "$annoying_nodebug" = "onlydothisaftercompletingthebasics" ] || grep 'docker\|lxc' /proc/1/cgroup >/dev/null 2>&1; then
                echo Run this script locally with debugging details.
            else
                if [ "$language" = "cpp" ]; then
                    # http://mywiki.wooledge.org/BashFAQ/050
                    debug_cmd=(gdb '--eval-command="break main"' --args "${prog_name[@]}")
                elif [ "$language" = "python" ]; then
                    debug_cmd=("$pudb3" "$1" "$main_file_arguments")
                elif [ "$language" = "bash" ]; then
                    debug_cmd=(bash -x "$1" "$main_file_arguments")
                    # TODO a real bash debugger like bashdb?
                fi
                echo -e "\nHit enter to run the following to show you your non-caputred output:\n\t$ $MAGENTA" "${prog_name[@]}" "<$testpath$RESET"
                read -r
                echo ">>>>your output>>>>"
                "${prog_name[@]}" <"$testpath"
                check_hashes
                echo "<<<<your output<<<<"
                echo -e "\nHit enter to see the differences between your caputred standard out and the goal."
                echo "Type$MAGENTA esc :qa$RESET to leave Vim when you are done."
                read -r
                # Either meld or vim works, up to you!
                # meld --diff "stdio_tests/goals/$testname"_output.txt stdio_tests/outputs/"$testname"_output.txt &
                vim -d "stdio_tests/goals/$testname"_output.txt stdio_tests/outputs/"$testname"_output.txt
                echo -e "\nHit enter to continue into the debugger, which we launched here:"
                echo -e "\t$ $MAGENTA" "${debug_cmd[@]}" "$RESET"
                echo -e "while YOU copy the contents of $ $MAGENTA cat $testpath $RESET by hand"
                read -r
                "${debug_cmd[@]}"
                check_hashes
            fi
        fi
    done
    if [ "$language" = "cpp" ]; then
        rm -f "${prog_name[@]}"
    fi
}

arg_tests() {
    section
    echo "Running argument-based tests, if any:"
    # Tests a python script (first and only arg) against directory of std-in/out
    # Saves outputs and diffs
    # Usage: arg_tests main_file.py

    # For C++, build the student's main()
    if [ "$language" = "cpp" ]; then
        prog_name=("./program")
        # g++ -Wall -Werror -Wpedantic -g -std=c++14 $1 -o "$prog_name"
        # TODO: Can this be any more discerning, in case of multiple main()s?
        g++ -Wall -Werror -Wpedantic -g -std=c++14 ./*.cpp -o "${prog_name[0]}"
    elif [ "$language" = "python" ]; then
        prog_name=(python3 "$1")
    elif [ "$language" = "bash" ]; then
        prog_name=(bash "$1")
    fi

    rm -rf arg_tests/outputs/*
    for testpath in arg_tests/args/*.txt; do
        filename=$(basename "$testpath")
        testname="${filename%_*}"
        read -ra testargs <"$testpath"
        subsection
        echo -e "We're running: $ $MAGENTA" "${prog_name[@]}" "${testargs[@]}" "$RESET"
        t0=$(date +%s.%N)
        timeout 20 "${prog_name[@]}" "${testargs[@]}"
        check_hashes
        echo -e "Your program took the following number of seconds to run the main driver on a sample input:"
        echo -e "print($(date +%s.%N) - $t0)" | python3
        diff -y -W 200 arg_tests/goals/"$testname"_output.txt arg_tests/outputs/"$testname"_output.txt >arg_tests/diffs/"$testname".txt
        vimdiff arg_tests/goals/"$testname"_output.txt arg_tests/outputs/"$testname"_output.txt -c TOhtml -c "w! arg_tests/diffs/$testname.html" -c 'qa!' >/dev/null 2>&1
        if [ "$fuzzy_partial_credit" = false ]; then
            echo Diffs are computed rigidly -- no partial credit!
            diff arg_tests/goals/"$testname"_output.txt arg_tests/outputs/"$testname"_output.txt >/dev/null 2>&1
            grade_update "$testpath" 100 0
            # Just a useless placeholder here:
            fuzzy_diff=0
        else
            echo Diffs are computed fuzzy -- with partial credit!
            fuzzy_diff=$(python3 .admin_files/fuzzydiffer.py "arg_tests/goals/$testname"_output.txt arg_tests/outputs/"$testname"_output.txt)
            grade_update "$testpath" "$fuzzy_diff" 0
        fi
        diff stdio_tests/goals/"$testname"_output.txt stdio_tests/outputs/"$testname"_output.txt >/dev/null 2>&1
        if [ "$?" -eq 0 ] || [ "$fuzzy_diff" -eq 100 ]; then
            # bash's no-op is most clear positive logic here...
            :
        else
            if [ "$annoying_nodebug" = "onlydothisaftercompletingthebasics" ] || grep 'docker\|lxc' /proc/1/cgroup >/dev/null 2>&1; then
                echo Run this script locally with debugging details.
            else
                if [ "$language" = "cpp" ]; then
                    # http://mywiki.wooledge.org/BashFAQ/050
                    debug_cmd=(gdb '--eval-command="break main"' --args "${prog_name[@]}" "${testargs[@]}")
                elif [ "$language" = "python" ]; then
                    debug_cmd=("$pudb3" "$1" "${testargs[@]}")
                elif [ "$language" = "bash" ]; then
                    debug_cmd=(bash -x "$1" "${testargs[@]}")
                    # TODO a real bash debugger like bashdb?
                fi
                echo -e "\nHit enter to see the differences between your argument-based output and ours."
                echo "Type$MAGENTA esc :qa$RESET to leave Vim when you are done."
                read -r
                # Either meld or vim works, up to you!
                # meld --diff "arg_tests/goals/$testname"_output.txt arg_tests/outputs/"$testname"_output.txt &
                vim -d "arg_tests/goals/$testname"_output.txt arg_tests/outputs/"$testname"_output.txt
                echo -e "\nHit enter to continue into the debugger, which we launched as follows:"
                echo -e "\t$ $MAGENTA" "${debug_cmd[@]}" "$RESET"
                read -r
                "${debug_cmd[@]}"
                check_hashes
            fi
        fi
    done
    if [ "$language" = "cpp" ]; then
        rm -f "${prog_name[@]}"
    fi
}

files_exist() {
    # https://stackoverflow.com/questions/4069188/how-to-pass-an-associative-array-as-argument-to-a-function-in-bash
    # https://stackoverflow.com/questions/3112687/how-to-iterate-over-associative-arrays-in-bash
    section
    echo "Test for existence of files and their type data, if any:"
    local -n arr=$1
    for exist_file in "${!arr[@]}"; do
        echo -e "\t*" "$exist_file" existence with "${arr["$exist_file"]}" "?"
        [ -f "$exist_file" ] && file "$exist_file" | grep "${arr["$exist_file"]}" >/dev/null 2>&1
        grade_update \""$exist_file\" with type containing \"${arr["$exist_file"]}\" existed" 100 0
    done
}

######## Init -> ########
annoying_nodebug=$1
num_tests=0
grade=0
student_file="results.txt"
echo -e "Summary of tests follows, in recommended order of completion:\n" >$student_file

check_hashes

if [ ! "$(uname)" = Linux ]; then
    echo "Run this on a Linux platform!"
    exit 1
fi

# Some OS's (OpenSuse) install pudb3 as pudb
if command -v pudb3 >/dev/null 2>&1; then
    pudb3=pudb3
else
    pudb3=pudb
fi

if ! grep 'docker\|lxc' /proc/1/cgroup >/dev/null 2>&1; then
    if [ "$language" = "cpp" ]; then
        :
        # TODO Find a good C++ flowchart generator and run here
    elif [ "$language" = "python" ]; then
        section
        echo You may find the following Control Flow Graphs helpful in thinking about your code:
        echo Install with: $ "$MAGENTA" pip3 install py2cfg --user"$RESET"
        echo Files to check out include:
        for pyfile in *.py; do
            py2cfg "$pyfile"
        done
        ls ./*.svg
        # xdg-open ./*.svg
    elif [ "$language" = "bash" ]; then
        :
        # TODO A flowchart generator for bash does not likely exist...
    fi
fi
######## <- Init ########

######## Standard tests -> ########
shopt -s nullglob
unit_tests
stdio_tests "$main_file"
arg_tests "$main_file"
files_exist file_arr
shopt -u nullglob
######## <- Standard tests ########

######## Static analysis -> ########
if [ "$enable_static_analysis" = true ]; then
    section
    echo -e "If you see output below here, it's suggestions about static analysis:"
    if [ "$language" = "cpp" ]; then
        cppcheck --enable=all --error-exitcode=1 --language=c++ ./*.cpp ./*.h ./*.hpp
    elif [ "$language" = "python" ]; then
        mypy --strict --disallow-any-explicit ./*.py
    elif [ "$language" = "bash" ]; then
        shellcheck --check-sourced --external-sources "$main_file"
    fi
    grade_update "static analysis / typechecking" 100 0
fi
######## <- Static analysis ########

######## Format check -> ########
if [ "$enable_format_check" = true ]; then
    section
    echo -e "If you see output below here, it's suggestions about code formatting style:"
    shopt -s nullglob
    if [ "$language" = "cpp" ]; then
        python3 .admin_files/run-clang-format.py -r --style=LLVM --exclude './.admin_files/build/*' .
        # CI needed this script instead of local command?
        # clang-format --dry-run --Werror --style=Microsoft *.cpp *.h *.hpp
    elif [ "$language" = "python" ]; then
        black --check ./*.py
    elif [ "$language" = "bash" ]; then
        # https://www.arachnoid.com/linux/beautify_bash/
        # https://github.com/mvdan/sh#shfmt
        # Format dir with: ./go/bin/shfmt -i 4 -w .
        if [ -x ./shfmt ]; then
            ./shfmt -i 4 -d .
        elif command -v shfmt >/dev/null 2>&1; then
            shfmt -i 4 -d .
        else
            echo "Install shfmt to run the Bash format check!"
            (exit 1)
        fi
    fi
    grade_update "auto-format style check" 100 0
    shopt -u nullglob
fi
######## <- Format check ########

######## Variable custom tests -> ########
section
echo Custom tests, if any, follow here:
for func in $(compgen -A function); do
    if grep -q "^custom_test" - <<<"$func"; then
        custom_test_score=-1
        check_hashes
        $func
        check_hashes
        if [ "$custom_test_score" -ne "-1" ]; then
            grade_update "$func" "$custom_test_score" 0
        fi
    fi
done
######## <- Variable custom tests ########

######## Cleanup -> ########
rm -rf __pycache__
rm -rf .admin_files/__pycache__
rm -rf .admin_files/build
rm -rf .mypy_cache
rm -rf unit_tests/.mypy_cache
######## <- Cleanup ########

######## Reporting and grading -> ########
grade=$(echo "print(int($grade / $num_tests))" | python3)
echo -e "Your total grade is:\n$grade" >>$student_file
section
cat $student_file
if [ -f student_git_pass_threshold.txt ]; then
    pass_threshold=$(cat student_git_pass_threshold.txt)
    check_hashes
else
    pass_threshold=70
fi
notdone=$(python3 -c "print($grade < $pass_threshold)")
check_hashes
perfect=$(python3 -c "print($grade == 100)")
if [ "$notdone" == "True" ]; then
    echo -e "$RED\nYou're not passing yet.$RESET"
    echo -e "To see why, actually read the above output!\n"
    exit 1
else
    if [ "$perfect" == "True" ]; then
        echo -e "$GREEN\nIt's perfect!\n$RESET"
    else
        echo -e "$GREEN\nYou're passing; decide how much you want the extra points!\n$RESET"
    fi
    echo "The last step is to push your changes to git-classes:"
    echo -e "    Make sure the CI passes, turns green, and you inspect the job itself for your grade."
    echo -e "    Your repo will turn green with a grade of $pass_threshold (set in student_git_pass_threshold.txt)."
    echo -e "    Actually look at the Gitlab CI details to see what we think your current grade is."
    echo -e "    Unless you see the output and numerical grade above on Gitlab, do not assume you are done!\n"
    exit 0
fi
######## <- Reporting and grading ########
