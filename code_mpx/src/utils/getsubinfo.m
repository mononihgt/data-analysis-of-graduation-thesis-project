function subinfo = getsubinfo

prompt = {'编号','性别（1=男性，2=女性）','年龄','姓名','利手（1=右手，2=左手）'};
dlg_title = 'subInfo';
num_line = [1 50];    % [行数, 宽度(字符数)]，把宽度改大可以增大对话框
def_answer = {'1','1','18','cyy','1'};
subinfo = inputdlg(prompt,dlg_title,num_line,def_answer);

if isempty(subinfo)
    error('getsubinfo:Cancelled','用户已取消，程序终止。');
end

end