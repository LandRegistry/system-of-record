#!/bin/bash

release=$1

#return merge info from git since the last release
text=$(git log develop $release..HEAD --pretty=format:"- %cd - %s%b%n" --merges --simplify-merges --date="short")

slug_release="${release//./_}"

#if we have merge info create a release note
if [ "$text" != "" ]; then

    #grab a local copy of the wiki so we can update the release info
    git clone git@git.lr.net:register-migration/system-of-record.wiki.git

    #create the release note file and slug name
    cd system-of-record.wiki
    md_file_name="$slug_release""_system_of_record.markdown"
    slug="$slug_release""_release_note_system_of_record"

    #create the release note markdown file
    echo "$text" >> "$md_file_name"

    #add the new release link to the release page
    echo "" >> home.markdown
    echo "["$release"]("$slug")" >> home.markdown

    #add, commit and push the wiki
    git add .
    git commit -m "Release note added to wiki"
    git push origin
fi