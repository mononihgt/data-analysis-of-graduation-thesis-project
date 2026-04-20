try
    clear all;

    %设置文件路径
    s = pwd;
    addpath(genpath(s));
    path.ori = s;
    path.face = [s '\Stimuli\face'];
    path.intro = [s '\Stimuli\intro'];
    path.DJtask_data = [s '\DJtask_data'];


    subinfo = getsubinfo;

%% 
    % 设置参数
    [fix,key,rgb,win,winRect,width,height,sizes,Rect_DJtask] = load_DJpara();
    f = load('facelist.mat');
    f = f.facelist;
    facelist = f(str2double(char(subinfo(1))));
    facelist = facelist{1};
    % 加载图片 
    for i = 1:6
        Ftex{i}=load_image(win,path.face,facelist{i},path.ori);
    end

    trialTable = readtable('DJtasktriallist.xlsx');
    triallist = table2struct(trialTable);
    for i =1:12
        order(2*(i-1)+1:2*(i-1)+2,1) = shuffle(1:2);
    end
    order(25:56,1)=ones([32,1]);
    for i = 1:length(triallist)
        triallist(i).order = order(i);
    end
    [~, idx] = sort([triallist.type]);  % 获取排序索引
    triallist = triallist(idx);
    num=randperm(24,8);
    praclist=shuffle(triallist(num));
    triallist(num)=[];
    triallist = shuffle(triallist);
    
    %% 练习
    Wtex{1}=load_image(win,path.intro,'true.png',path.ori);
    Wtex{2}=load_image(win,path.intro,'false.png',path.ori);

    prac_intro_tex=load_image(win, path.intro, 'prac_intro.png', path.ori);
    [screenWidth, screenHeight] = Screen('WindowSize', win);
    [imageWidth, imageHeight] = Screen('WindowSize', prac_intro_tex);
    prac_intro_rect = CenterRectOnPoint([0, 0, imageWidth, imageHeight], screenWidth/2, screenHeight/2);
    Screen('Drawtexture',win,prac_intro_tex,[],prac_intro_rect);
    Screen('Flip', win);
    key_space(key)

    demo_DJprac(win,winRect,key,Ftex,Rect_DJtask,praclist,subinfo,Wtex);

    %练习结束
    exp_intro_tex=load_image(win, path.intro, 'exp_intro.png', path.ori);
    [screenWidth, screenHeight] = Screen('WindowSize', win);
    [imageWidth, imageHeight] = Screen('WindowSize', exp_intro_tex);
    exp_intro_rect = CenterRectOnPoint([0, 0, imageWidth, imageHeight], screenWidth/2, screenHeight/2);
    Screen('Drawtexture',win,exp_intro_tex,[],exp_intro_rect);
    Screen('Flip', win);
    key_space(key)
    
    %% 正式实验
    result = demo_DJtask(win,winRect,key,Ftex,Rect_DJtask,triallist,subinfo);

    %% 输出数据
    if ~isempty(result)
        columheader={'SubNo','Name','Gender','Age','Handedness',...
            'F0','F1','F2','F0V','F1V','F2V','type','order','correct_ans',...
            'answer','acc','rt'};
        result = orderfields(result,columheader);
        ret = [columheader;(struct2cell(result))'];
        cd(path.DJtask_data);
        currentDate = datestr(now, 'yyyy-mm-dd');

        T = cell2table(ret);
        csvFileName = ['DJtask-',char(subinfo(1)),'-',currentDate,'.csv']
        writetable(T, csvFileName, 'WriteVariableNames', false);

        % xlswrite(['DJtask-',char(subinfo(1)),'-',currentDate,'.xlsx'],ret);
        save(['DJtask-',char(subinfo(1)),'-',currentDate,'.mat'],'ret');
        cd(path.ori);
    else
        error('no data')
    end
    
    sca;

    %% 改
    mean_acc = mean([result([result.type] == 1).acc]);
    disp(['平均准确率1: ', num2str(mean_acc)]);
    mean_acc = mean([result([result.type] == 3).acc]);
    disp(['平均准确率3: ', num2str(mean_acc)]);

catch    
    ShowCursor;
    Screen('CloseAll');
    psychrethrow(lasterror);
end
