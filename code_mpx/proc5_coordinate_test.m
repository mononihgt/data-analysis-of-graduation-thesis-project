try
    clear all;

    %设置文件路径
    s = pwd;
    addpath(genpath(s));
    path.ori = s;
    path.face = [s '\Stimuli\face'];
    path.CTtask_data = [s '\CTtask_data'];
    path.intro = [s '\Stimuli\intro'];


    subinfo = getsubinfo;

%% 
    % 设置参数
    [fix,key,rgb,win,winRect,width,height,sizes,Rect_EPtask,facebar] = load_EPpara;
    f = load('facelist.mat');
    f = f.facelist;
    facelist = f(str2double(char(subinfo(1))));
    facelist = facelist{1};
    % 加载图片 
    for i = 1:6
        Ftex{i}=load_image(win,path.face,facelist{i},path.ori);
    end
    
%% 坐标记忆测试任务
    Wtex{1}=load_image(win,path.intro,'true.png',path.ori);
    Wtex{2}=load_image(win,path.intro,'false.png',path.ori);

    exp_intro_tex=load_image(win, path.intro, 'exp_intro.png', path.ori);
    [screenWidth, screenHeight] = Screen('WindowSize', win);
    [imageWidth, imageHeight] = Screen('WindowSize', exp_intro_tex);
    exp_intro_rect = CenterRectOnPoint([0, 0, imageWidth, imageHeight], screenWidth/2, screenHeight/2);
    Screen('Drawtexture',win,exp_intro_tex,[],exp_intro_rect);
    Screen('Flip', win);
    key_space(key)

    result = demo_EPtest2(win,winRect,rgb,Rect_EPtask.square,key,Ftex,Rect_EPtask.testF,facebar,subinfo);

    if ~isempty(result)
        columheader={'SubNo','Name','Gender','Age','Handedness','face',...
            'true_leftBar','true_rightBar','leftBarLength','rightBarLength',...
            'error','acc','rt'};
        result = orderfields(result,columheader);
        ret = [columheader;(struct2cell(result))'];
        cd(path.CTtask_data);
        currentDate = datestr(now, 'yyyy-mm-dd');
        T = cell2table(ret);
        csvFileName = ['CTtask-',char(subinfo(1)),'-',currentDate,'.csv'];
        writetable(T, csvFileName, 'WriteVariableNames', false);
        % xlswrite(['CTtask-',char(subinfo(1)),'-',currentDate,'.xlsx'],ret);
        save(['CTtask-',char(subinfo(1)),'-',currentDate,'.mat'],'ret');
        cd(path.ori);
    end
    ShowCursor;
    sca;

catch    
    ShowCursor;
    Screen('CloseAll');
    psychrethrow(lasterror);
end 
