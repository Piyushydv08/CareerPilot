with open('app/analyze/page.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

scroll_msg_lines = """
      {resumeData && jobInput.trim() && (
        <div className="flex items-center justify-center mb-8 opacity-80 animate-fade-in">
          <div className="h-px bg-gradient-to-r from-transparent via-cyber-blue/40 to-transparent flex-1 max-w-[200px]" />
          <span className="px-4 font-mono text-[11px] font-bold text-cyber-blue uppercase tracking-widest text-center animate-pulse">
            Scroll down to see your full ATS breakdown
          </span>
          <div className="h-px bg-gradient-to-r from-transparent via-cyber-blue/40 to-transparent flex-1 max-w-[200px]" />
        </div>
      )}
""".splitlines(True)

# Extract blocks
ats_block = lines[681:700]
jobs_block = lines[740:861]

# Delete blocks (in reverse order to preserve indices)
del lines[740:861]
del lines[681:700]

# Insert scroll msg at index 421
lines[421:421] = scroll_msg_lines

# Find the end of the file.
# The last 4 lines are:
#         </div>
#       </div>
#     </div>
#   );
# }
# We want to insert after the second to last `</div>` (the one closing the grid).
# Let's search from the end for "      </div>"
insert_idx = -1
for i in range(len(lines)-1, -1, -1):
    if lines[i].startswith("      </div>"):
        insert_idx = i + 1
        break

if insert_idx != -1:
    container_start = ['\n      {/* Bottom Centered Sections */}\n', '      <div className="flex flex-col gap-8 max-w-4xl mx-auto mt-8 w-full">\n']
    container_end = ['      </div>\n']
    lines[insert_idx:insert_idx] = container_start + ats_block + ['\n'] + jobs_block + container_end
else:
    print("Could not find insertion point")

with open('app/analyze/page.tsx', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Done")
