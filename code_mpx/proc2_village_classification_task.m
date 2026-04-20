try
    clear all;

    %设置文件路径
    s = pwd;
    addpath(genpath(s));
    path.ori = s;
    path.face = [s '\Stimuli\face'];
    path.intro = [s '\Stimuli\intro'];
    path.SPtask1_data = [s '\SPtask1_data'];


    subinfo = getsubinfo;

%% 
    % 设置参数
    [fix,key,rgb,win,winRect,width,height,sizes,Rect_SPtask,facebar] = load_SPpara;
    f = load('facelist.mat');
    f = f.facelist;
    facelist = f(str2double(char(subinfo(1))));
    facelist = facelist{1};
    % 加载图片 
    for i = 1:6
        Ftex{i}=load_image(win,path.face,facelist{i},path.ori);
    end

    intro_name = {['SP_QA.png'] ['SP_QB.png'] ['SP_QC.png']};
    for i = 1:3
        intro_tex{i} = load_image(win,path.intro,intro_name{i},path.ori);
    end
        
    %% 村庄分类任务
    [SP_1_result] = demo_SPtask(win,winRect,Ftex,Rect_SPtask,intro_tex,subinfo);

    %% 改
    if ~isempty(SP_1_result)
        columheader={'SubNo','Name','Gender','Age','Handedness',...
            'village','face1','face2',...
            'false_time','rt','mean_false','mean_rt','block'};
        result = orderfields(SP_1_result,columheader);
        ret = [columheader;(struct2cell(result))'];
        cd(path.SPtask1_data);
        T = cell2table(ret);
        currentDate = datestr(now, 'yyyy-mm-dd');
        csvFileName = ['SPtask1-',char(subinfo(1)),'-',currentDate,'.csv'];
        writetable(T, csvFileName, 'WriteVariableNames', false);
        % xlswrite(['SPtask1-',char(subinfo(1)),'.xlsx'],ret);
        save(['SPtask1-',char(subinfo(1)),'.mat'],'ret');
        cd(path.ori);
    else
        error('no data')
    end

    sca;

catch    
    ShowCursor;
    Screen('CloseAll');
    psychrethrow(lasterror);
end
